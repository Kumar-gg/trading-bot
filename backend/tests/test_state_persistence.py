import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import Bot, Run


@pytest.mark.feature
async def test_stop_start_keeps_same_run_and_position(client: AsyncClient):
    create = await client.post(
        "/api/bots",
        json={"name": "Persist", "template_id": "ema_trend", "initial_capital": 5000},
    )
    assert create.status_code == 200
    body = create.json()
    bot_id = body["id"]
    run_id = body["current_run_id"]

    await client.post(f"/api/bots/{bot_id}/start")
    await client.post(f"/api/bots/{bot_id}/stop")
    after_stop = await client.get(f"/api/bots/{bot_id}")
    assert after_stop.json()["status"] == "idle"
    assert after_stop.json()["current_run_id"] == run_id

    await client.post(f"/api/bots/{bot_id}/start")
    after_start = await client.get(f"/api/bots/{bot_id}")
    assert after_start.json()["status"] == "running"
    assert after_start.json()["current_run_id"] == run_id

    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        run = await session.get(Run, run_id)
        assert run is not None
        assert run.ended_at is None


@pytest.mark.feature
async def test_running_status_survives_api_reread(client: AsyncClient):
    """Simulates closing UI and reopening: state comes from DB, not memory."""
    create = await client.post("/api/bots", json={"name": "Reopen", "template_id": "ema_trend"})
    bot_id = create.json()["id"]
    await client.post(f"/api/bots/{bot_id}/start")

    r1 = await client.get("/api/bots")
    r2 = await client.get("/api/bots")
    b1 = next(b for b in r1.json() if b["id"] == bot_id)
    b2 = next(b for b in r2.json() if b["id"] == bot_id)
    assert b1["status"] == "running"
    assert b2["status"] == "running"
    assert b1["current_run_id"] == b2["current_run_id"]


@pytest.mark.feature
async def test_reset_archives_run(client: AsyncClient):
    create = await client.post("/api/bots", json={"name": "ResetMe", "template_id": "ema_trend"})
    bot_id = create.json()["id"]
    old_run = create.json()["current_run_id"]
    await client.post(f"/api/bots/{bot_id}/reset")
    after = (await client.get(f"/api/bots/{bot_id}")).json()
    assert after["current_run_id"] != old_run

    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        old = await session.get(Run, old_run)
        assert old is not None
        assert old.ended_at is not None
