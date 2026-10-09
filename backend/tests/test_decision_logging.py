import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import Bot


@pytest.mark.feature
async def test_decision_log_created_on_manual_eval(client: AsyncClient):
    from app.engine.bot_worker import BotEngine
    from app.main import app
    from app.market.candles import Candle

    create = await client.post(
        "/api/bots",
        json={"name": "Dec Bot", "template_id": "ema_trend", "timeframe": "5m"},
    )
    assert create.status_code == 200
    bot_id = create.json()["id"]
    await client.post(f"/api/bots/{bot_id}/start")

    engine: BotEngine = app.state.engine
    market = app.state.market
    market.mark_stream_update("BTCUSDT", "5m")
    market._last_prices["BTCUSDT"] = 100_000.0

    candle = Candle(
        open_time=1_700_000_000_000,
        open=100_000.0,
        high=100_100.0,
        low=99_900.0,
        close=100_050.0,
        volume=10.0,
        closed=True,
    )

    from app.db.session import SessionLocal
    from app.market.candles import Candle as CacheCandle, upsert_candles

    history = [
        CacheCandle(
            open_time=1_700_000_000_000 + i * 300_000,
            open=100_000.0 + i,
            high=100_100.0 + i,
            low=99_900.0 + i,
            close=100_050.0 + i,
            volume=1.0,
        )
        for i in range(80)
    ]

    async with SessionLocal() as session:
        await upsert_candles(session, "BTCUSDT", "5m", history)
        bot = await session.get(Bot, bot_id)
        assert bot is not None
        await engine._evaluate_bot(session, bot, candle)
        await session.commit()

    logs = await client.get(f"/api/decisions?bot_id={bot_id}")
    assert logs.status_code == 200
    items = logs.json()
    assert len(items) >= 1
    last = items[0]
    assert last["decision"] in ("HOLD", "BUY", "SELL", "REJECTED")
    assert "indicators" in last
    assert last["btc_price"] == 100_000.0


@pytest.mark.unit
async def test_decisions_api_filter(client: AsyncClient):
    create = await client.post("/api/bots", json={"name": "F", "template_id": "ema_trend"})
    bot_id = create.json()["id"]
    r = await client.get("/api/decisions", params={"bot_id": bot_id, "decision": "HOLD"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
