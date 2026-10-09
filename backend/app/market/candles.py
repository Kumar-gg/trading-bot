from dataclasses import dataclass

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CandleCache


@dataclass
class Candle:
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool = True


def candles_to_dataframe(candles: list[Candle]) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame(columns=["open_time", "open", "high", "low", "close", "volume"])
    rows = [
        {
            "open_time": c.open_time,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in candles
    ]
    return pd.DataFrame(rows)


async def upsert_candles(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    candles: list[Candle],
) -> None:
    for c in candles:
        stmt = insert(CandleCache).values(
            symbol=symbol,
            timeframe=timeframe,
            open_time=c.open_time,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
            closed=c.closed,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timeframe", "open_time"],
            set_={
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "closed": c.closed,
            },
        )
        await session.execute(stmt)


async def load_candles(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    limit: int = 500,
) -> list[Candle]:
    result = await session.execute(
        select(CandleCache)
        .where(CandleCache.symbol == symbol, CandleCache.timeframe == timeframe)
        .order_by(CandleCache.open_time.desc())
        .limit(limit)
    )
    rows = list(reversed(result.scalars().all()))
    return [
        Candle(
            open_time=r.open_time,
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            volume=r.volume,
            closed=r.closed,
        )
        for r in rows
    ]
