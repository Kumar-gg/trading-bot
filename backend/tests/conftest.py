"""Test bootstrap: isolated DB + mocked Binance before app import."""
from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncGenerator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

_fd, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["TB_DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH.replace(chr(92), '/')}"


@pytest.fixture(scope="session", autouse=True)
def _patch_market_data() -> None:
    from app.market.binance_ws import MarketDataService

    async def fake_start(self: MarketDataService) -> None:
        self._running = True
        self.rest_ok = True
        self.ws_connected = False
        self.last_error = None

    async def fake_stop(self: MarketDataService) -> None:
        self._running = False
        self.ws_connected = False
        self._task = None

    async def fake_check(self: MarketDataService) -> bool:
        self.rest_ok = True
        return True

    def fake_mark_stream(self: MarketDataService, symbol: str, timeframe: str) -> None:
        from datetime import datetime, timezone

        self._last_kline_at[(symbol.upper(), timeframe)] = datetime.now(timezone.utc)
        self._last_prices["BTCUSDT"] = 100_000.0

    MarketDataService.mark_stream_update = fake_mark_stream  # type: ignore[method-assign]

    async def fake_fetch(
        self: MarketDataService, symbol: str, timeframe: str, limit: int = 500
    ) -> list:
        from app.market.candles import Candle

        self.rest_ok = True
        base = 100_000.0
        return [
            Candle(
                open_time=1_700_000_000_000 + i * 300_000,
                open=base,
                high=base + 100,
                low=base - 100,
                close=base + 50,
                volume=10.0,
                closed=True,
            )
            for i in range(min(limit, 60))
        ]

    MarketDataService.start = fake_start  # type: ignore[method-assign]
    MarketDataService.stop = fake_stop  # type: ignore[method-assign]
    MarketDataService.check_rest = fake_check  # type: ignore[method-assign]
    MarketDataService.fetch_historical_klines = fake_fetch  # type: ignore[method-assign]


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    from app.main import app

    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
