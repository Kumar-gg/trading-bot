import pytest
from httpx import AsyncClient


@pytest.mark.smoke
async def test_health(client: AsyncClient):
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "market_rest" in body


@pytest.mark.smoke
async def test_strategies_list(client: AsyncClient):
    r = await client.get("/api/strategies")
    assert r.status_code == 200
    strategies = r.json()
    assert len(strategies) >= 7
    ids = {s["id"] for s in strategies}
    assert "ema_trend" in ids
    assert "macd_trend" in ids
    assert all(s.get("category") for s in strategies)
    assert all(s.get("params_schema") for s in strategies)


@pytest.mark.smoke
async def test_settings(client: AsyncClient):
    r = await client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert "fee_bps" in data
    assert "rest_ok" in data
