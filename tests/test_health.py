from httpx import AsyncClient


async def test_health_live(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


async def test_health_ready_ok(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_health_ready_503_when_es_down(client_dead_es: AsyncClient) -> None:
    response = await client_dead_es.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
