import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.cli.__main__ import import_csv
from app.models.post import Post
from app.repositories.db import create_engine
from app.repositories.es import create_es_client
from app.settings import get_settings


@pytest.fixture
async def data_ready() -> None:
    await import_csv("/data/posts.csv")


async def test_delete_removes_post_and_is_idempotent(
    client: AsyncClient, data_ready: None
) -> None:
    first = await client.delete("/posts/1")
    assert first.status_code == 204

    search = await client.post("/search", json={"query": "Булл"})
    assert search.json()["items"] == []

    second = await client.delete("/posts/1")
    assert second.status_code == 204


async def test_delete_retry_cleans_leftover_index_document(
    client: AsyncClient, data_ready: None
) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(delete(Post).where(Post.id == 1))
    finally:
        await engine.dispose()

    es = create_es_client(settings.es_url)
    try:
        count_before = await es.count(index=settings.es_index_name)
    finally:
        await es.close()
    assert count_before["count"] >= 1500

    response = await client.delete("/posts/1")
    assert response.status_code == 204

    search = await client.post("/search", json={"query": "Булл"})
    assert search.json()["items"] == []


async def test_delete_returns_503_when_es_down(client_dead_es: AsyncClient) -> None:
    response = await client_dead_es.delete("/posts/1")
    assert response.status_code == 503
    assert "traceback" not in response.text.lower()
