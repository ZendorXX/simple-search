import pytest
from httpx import AsyncClient

from app.cli.__main__ import import_csv
from app.repositories.es import create_es_client
from app.settings import get_settings


@pytest.fixture
async def data_ready() -> None:
    await import_csv("/data/posts.csv")


async def test_search_finds_russian_word_and_word_form(
    client: AsyncClient, data_ready: None
) -> None:
    response = await client.post("/search", json={"query": "Булл"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert any("Булл" in item["text"] for item in items)

    response = await client.post("/search", json={"query": "Булла"})
    assert response.status_code == 200
    assert response.json()["items"]


async def test_search_finds_english_token(
    client: AsyncClient, data_ready: None
) -> None:
    response = await client.post("/search", json={"query": "WhatsApp"})
    assert response.status_code == 200
    assert response.json()["items"]


async def test_search_rejects_blank_query(client: AsyncClient) -> None:
    response = await client.post("/search", json={"query": "   \n\t "})
    assert response.status_code == 422


async def test_search_no_matches_returns_empty_items(
    client: AsyncClient, data_ready: None
) -> None:
    response = await client.post("/search", json={"query": "zzzzqqqxx"})
    assert response.status_code == 200
    assert response.json() == {"items": []}


async def test_search_limit_order_and_full_fields(
    client: AsyncClient, data_ready: None
) -> None:
    response = await client.post("/search", json={"query": "WhatsApp"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert 1 <= len(items) <= 20
    for item in items:
        assert set(item.keys()) == {"id", "rubrics", "text", "created_date"}
        assert isinstance(item["rubrics"], list)
        assert all(isinstance(r, str) for r in item["rubrics"])
    for newer, older in zip(items, items[1:]):
        assert newer["created_date"] >= older["created_date"]
        if newer["created_date"] == older["created_date"]:
            assert newer["id"] < older["id"]


async def test_search_does_not_leak_ghost_documents(
    client: AsyncClient, data_ready: None
) -> None:
    settings = get_settings()
    es = create_es_client(settings.es_url)
    try:
        await es.index(
            index=settings.es_index_name,
            id="999999",
            document={
                "id": 999999,
                "text": "ghostzzzmarker отсутствует в базе",
                "created_date": "2030-01-01 00:00:00",
            },
        )
        await es.indices.refresh(index=settings.es_index_name)
        response = await client.post("/search", json={"query": "ghostzzzmarker"})
        assert response.status_code == 200
        assert response.json() == {"items": []}
    finally:
        try:
            await es.delete(index=settings.es_index_name, id="999999")
        except Exception as exc:
            if getattr(exc, "status_code", None) != 404:
                raise
        await es.close()


async def test_search_returns_503_when_es_down(client_dead_es: AsyncClient) -> None:
    response = await client_dead_es.post("/search", json={"query": "тест"})
    assert response.status_code == 503
    assert "traceback" not in response.text.lower()
