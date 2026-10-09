import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.db.models import JournalEvent, JournalEventType
from app.db.session import SessionLocal
from app.services.journal import try_log_journal


@pytest.mark.unit
async def test_journal_dedupe_prevents_duplicates():
    from app.db.models import Bot, Run

    async with SessionLocal() as session:
        bot = Bot(name="J", template_id="ema_trend")
        session.add(bot)
        await session.flush()
        run = Run(
            bot_id=bot.id,
            starting_equity=10_000,
            template_id="ema_trend",
            cash=10_000,
            peak_equity=10_000,
        )
        session.add(run)
        await session.flush()

        first = await try_log_journal(
            session,
            run,
            JournalEventType.decision,
            "HOLD",
            {"decision": "HOLD"},
            dedupe_key="decision:123",
            bot_id=bot.id,
        )
        second = await try_log_journal(
            session,
            run,
            JournalEventType.decision,
            "HOLD again",
            {"decision": "HOLD"},
            dedupe_key="decision:123",
            bot_id=bot.id,
        )
        await session.commit()
        assert first is not None
        assert second is None

        count = await session.scalar(
            select(func.count()).select_from(JournalEvent).where(JournalEvent.run_id == run.id)
        )
        assert count == 1


@pytest.mark.feature
async def test_journal_api_matches_stored_payload(client: AsyncClient):
    from app.db.models import Bot, Run

    async with SessionLocal() as session:
        bot = Bot(name="API", template_id="ema_trend", timeframe="5m")
        session.add(bot)
        await session.flush()
        run = Run(
            bot_id=bot.id,
            starting_equity=10_000,
            template_id="ema_trend",
            cash=10_000,
            peak_equity=10_000,
        )
        session.add(run)
        await session.flush()
        await try_log_journal(
            session,
            run,
            JournalEventType.regime_change,
            "Regime → trend (bull)",
            {
                "symbol": "BTCUSDT",
                "timeframe": "5m",
                "candle_open_time": 1_700_000_000_000,
                "trend": "bull",
                "regime": "trend",
                "adx": 25.0,
                "atr_pct": 1.2,
                "close": 100_000.0,
            },
            dedupe_key="regime_bar:1700000000000",
            bot_id=bot.id,
        )
        await session.commit()
        run_id = run.id
        bot_id = bot.id

    r = await client.get("/api/journal", params={"bot_id": bot_id})
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    row = next(x for x in items if x["event_type"] == "regime_change")
    assert row["payload"]["regime"] == "trend"
    assert row["payload"]["close"] == 100_000.0

    r2 = await client.get(f"/api/bots/runs/{run_id}/journal")
    assert r2.status_code == 200
    assert any(x["id"] == row["id"] for x in r2.json())


@pytest.mark.feature
async def test_journal_persists_across_bot_stop_start(client: AsyncClient):
    from app.db.models import Run

    create = await client.post("/api/bots", json={"name": "Persist", "template_id": "ema_trend"})
    bot_id = create.json()["id"]
    run_id = create.json()["current_run_id"]

    async with SessionLocal() as session:
        run = await session.get(Run, run_id)
        assert run is not None
        await try_log_journal(
            session,
            run,
            JournalEventType.bot_started,
            "started",
            {},
            dedupe_key=f"lifecycle:started:{run_id}",
            bot_id=bot_id,
        )
        await session.commit()

    await client.post(f"/api/bots/{bot_id}/start")
    await client.post(f"/api/bots/{bot_id}/stop")

    r = await client.get(f"/api/bots/runs/{run_id}/journal")
    assert r.status_code == 200
    types = {e["event_type"] for e in r.json()}
    assert "bot_started" in types
