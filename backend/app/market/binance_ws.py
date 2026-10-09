import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

import httpx
import websockets

from app.config import settings
from app.market.candles import Candle
from app.market.intervals import TIMEFRAME_MS, binance_interval

logger = logging.getLogger(__name__)

KlineHandler = Callable[[str, str, Candle, bool], Awaitable[None]]

# Fallback REST hosts if primary fails
REST_FALLBACKS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
]


class MarketDataService:
    def __init__(self) -> None:
        self._subscriptions: set[tuple[str, str]] = set()
        self._handlers: list[KlineHandler] = []
        self._task: asyncio.Task | None = None
        self._last_prices: dict[str, float] = {}
        self._running = False
        self.rest_ok: bool = False
        self.ws_connected: bool = False
        self.last_error: str | None = None
        self._last_kline_at: dict[tuple[str, str], datetime] = {}
        self._last_rest_at: datetime | None = None

    def subscribe(self, symbol: str, timeframe: str) -> None:
        self._subscriptions.add((symbol.upper(), timeframe))

    def unsubscribe_all(self) -> None:
        self._subscriptions.clear()

    def add_handler(self, handler: KlineHandler) -> None:
        self._handlers.append(handler)

    def get_mark_price(self, symbol: str) -> float | None:
        return self._last_prices.get(symbol.upper())

    def get_btc_price(self) -> float | None:
        return self._last_prices.get("BTCUSDT")

    def mark_stream_update(self, symbol: str, timeframe: str) -> None:
        self._last_kline_at[(symbol.upper(), timeframe)] = datetime.now(timezone.utc)

    def mark_rest_update(self) -> None:
        self._last_rest_at = datetime.now(timezone.utc)

    def market_data_age_sec(self, symbol: str, timeframe: str) -> float | None:
        ts = self._last_kline_at.get((symbol.upper(), timeframe))
        if not ts:
            return None
        return (datetime.now(timezone.utc) - ts).total_seconds()

    def last_market_update_at(self, symbol: str, timeframe: str) -> datetime | None:
        return self._last_kline_at.get((symbol.upper(), timeframe))

    def _rest_hosts(self) -> list[str]:
        hosts = [settings.binance_rest.rstrip("/")]
        for h in REST_FALLBACKS:
            if h.rstrip("/") not in hosts:
                hosts.append(h.rstrip("/"))
        return hosts

    async def fetch_historical_klines(
        self, symbol: str, timeframe: str, limit: int = 500
    ) -> list[Candle]:
        interval = binance_interval(timeframe)
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        last_exc: Exception | None = None
        for host in self._rest_hosts():
            url = f"{host}/api/v3/klines"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                candles: list[Candle] = []
                for row in data:
                    candles.append(
                        Candle(
                            open_time=int(row[0]),
                            open=float(row[1]),
                            high=float(row[2]),
                            low=float(row[3]),
                            close=float(row[4]),
                            volume=float(row[5]),
                            closed=True,
                        )
                    )
                    self._last_prices[symbol.upper()] = float(row[4])
                self.rest_ok = True
                self.last_error = None
                self.mark_rest_update()
                logger.info("Loaded %d klines from %s", len(candles), host)
                return candles
            except Exception as exc:
                last_exc = exc
                logger.warning("Binance REST failed (%s): %s", host, exc)
        self.rest_ok = False
        self.last_error = str(last_exc) if last_exc else "Unknown REST error"
        return []

    async def check_rest(self) -> bool:
        for host in self._rest_hosts():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.get(f"{host}/api/v3/ping")
                    r.raise_for_status()
                self.rest_ok = True
                self.last_error = None
                return True
            except Exception as exc:
                logger.warning("Ping failed %s: %s", host, exc)
        self.rest_ok = False
        self.last_error = "Cannot reach Binance market data (check internet / firewall)"
        return False

    def _stream_names(self) -> list[str]:
        streams = []
        for symbol, tf in self._subscriptions:
            streams.append(f"{symbol.lower()}@kline_{binance_interval(tf)}")
        return streams

    def _ws_url(self, streams: list[str]) -> str:
        base = settings.binance_ws.rstrip("/")
        if len(streams) == 1:
            return f"{base}/{streams[0]}"
        combined = base.replace("/ws", "/stream")
        if combined == base:
            combined = base + "/stream"
        return f"{combined}?streams={'/'.join(streams)}"

    async def _emit(self, symbol: str, timeframe: str, candle: Candle, is_closed: bool) -> None:
        self._last_prices[symbol] = candle.close
        if is_closed:
            self.mark_stream_update(symbol, timeframe)
        for h in self._handlers:
            try:
                await h(symbol, timeframe, candle, is_closed)
            except Exception:
                logger.exception("Kline handler error")

    async def _run_ws_loop(self) -> None:
        while self._running:
            streams = self._stream_names()
            if not streams:
                self.ws_connected = False
                await asyncio.sleep(1)
                continue
            url = self._ws_url(streams)
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    self.ws_connected = True
                    self.last_error = None
                    logger.info("Binance WS connected (%d streams)", len(streams))
                    async for raw in ws:
                        msg = json.loads(raw)
                        payload = msg.get("data", msg)
                        k = payload.get("k")
                        if not k:
                            continue
                        symbol = k["s"]
                        interval = k["i"]
                        tf = self._interval_from_binance(interval)
                        if tf is None:
                            continue
                        candle = Candle(
                            open_time=int(k["t"]),
                            open=float(k["o"]),
                            high=float(k["h"]),
                            low=float(k["l"]),
                            close=float(k["c"]),
                            volume=float(k["v"]),
                            closed=bool(k["x"]),
                        )
                        await self._emit(symbol, tf, candle, candle.closed)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.ws_connected = False
                self.last_error = str(exc)
                logger.exception("Binance WS disconnected; retrying in 3s")
                await asyncio.sleep(3)

    @staticmethod
    def _interval_from_binance(interval: str) -> str | None:
        mapping = {v: k for k, v in {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "1h": "1h",
            "4h": "4h",
        }.items()}
        return mapping.get(interval)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        await self.check_rest()
        self._task = asyncio.create_task(self._run_ws_loop())

    async def stop(self) -> None:
        self._running = False
        self.ws_connected = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


def bar_index(open_time: int, timeframe: str) -> int:
    ms = TIMEFRAME_MS.get(timeframe, 60_000)
    return open_time // ms
