import pytest
from httpx import AsyncClient


@pytest.mark.feature
async def test_bot_crud_and_lifecycle(client: AsyncClient):
    create = await client.post(
        "/api/bots",
        json={
            "name": "Test Bot",
            "symbol": "BTCUSDT",
            "timeframe": "5m",
            "template_id": "ema_trend",
            "params": {},
            "initial_capital": 5000,
        },
    )
    assert create.status_code == 200, create.text
    bot = create.json()
    bot_id = bot["id"]
    assert bot["name"] == "Test Bot"
    assert bot["status"] == "idle"
    assert bot["current_run_id"] is not None

    listed = await client.get("/api/bots")
    assert listed.status_code == 200
    assert any(b["id"] == bot_id for b in listed.json())

    got = await client.get(f"/api/bots/{bot_id}")
    assert got.status_code == 200

    start = await client.post(f"/api/bots/{bot_id}/start")
    assert start.status_code == 200
    assert start.json()["status"] == "running"

    pause = await client.post(f"/api/bots/{bot_id}/pause")
    assert pause.status_code == 200
    assert pause.json()["status"] == "paused"

    resume = await client.post(f"/api/bots/{bot_id}/start")
    assert resume.status_code == 200
    assert resume.json()["status"] == "running"

    stop = await client.post(f"/api/bots/{bot_id}/stop")
    assert stop.status_code == 200
    assert stop.json()["status"] == "idle"

    patch = await client.patch(
        f"/api/bots/{bot_id}",
        json={"name": "Renamed Bot", "params": {"ema_fast": 10}},
    )
    assert patch.status_code == 200
    assert patch.json()["name"] == "Renamed Bot"

    runs = await client.get(f"/api/bots/{bot_id}/runs")
    assert runs.status_code == 200
    assert len(runs.json()) >= 1

    reset = await client.post(f"/api/bots/{bot_id}/reset")
    assert reset.status_code == 200
    assert reset.json()["current_run_id"] is not None


@pytest.mark.feature
async def test_invalid_strategy_params_rejected(client: AsyncClient):
    r = await client.post(
        "/api/bots",
        json={
            "name": "Bad Params",
            "template_id": "ema_trend",
            "params": {"ema_fast": 999},
        },
    )
    assert r.status_code == 400


@pytest.mark.feature
async def test_cannot_patch_running_bot(client: AsyncClient):
    create = await client.post("/api/bots", json={"name": "Run Lock", "template_id": "ema_trend"})
    bot_id = create.json()["id"]
    await client.post(f"/api/bots/{bot_id}/start")
    patch = await client.patch(f"/api/bots/{bot_id}", json={"name": "Nope"})
    assert patch.status_code == 400
