import pytest
from httpx import AsyncClient


@pytest.mark.feature
async def test_compare_runs(client: AsyncClient):
    b1 = await client.post("/api/bots", json={"name": "C1", "template_id": "ema_trend"})
    b2 = await client.post("/api/bots", json={"name": "C2", "template_id": "macd_trend"})
    r1 = b1.json()["current_run_id"]
    r2 = b2.json()["current_run_id"]
    cmp_r = await client.post("/api/compare", json={"run_ids": [r1, r2]})
    assert cmp_r.status_code == 200
    data = cmp_r.json()
    assert len(data["metrics"]) == 2
    assert "insights" in data
    assert "series" in data
