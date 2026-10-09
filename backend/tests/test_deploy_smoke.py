import pytest
from httpx import AsyncClient


@pytest.mark.smoke
async def test_production_api_surface(client: AsyncClient):
    """Endpoints used by verify-api scripts after remote deploy."""
    for path in (
        "/api/health",
        "/api/bots",
        "/api/strategies",
        "/api/journal?limit=5",
        "/api/decisions?limit=5",
    ):
        r = await client.get(path)
        assert r.status_code == 200, path
