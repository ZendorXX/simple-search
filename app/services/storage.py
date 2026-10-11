from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.post import Post
from app.services.csv_reader import PostRow


def _es_actions(index_name: str, rows: list[PostRow]) -> list[dict]:
    return [
        {
            "_index": index_name,
            "_id": str(row.id),
            "_source": {
                "id": row.id,
                "text": row.text,
                "created_date": row.created_date.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }
        for row in rows
    ]


async def upsert_posts(engine: AsyncEngine, rows: list[PostRow]) -> None:
    values = [
        {
            "id": row.id,
            "text": row.text,
            "created_date": row.created_date,
            "rubrics": row.rubrics,
        }
        for row in rows
    ]
    statement = pg_insert(Post).values(values)
    statement = statement.on_conflict_do_update(
        index_elements=[Post.id],
        set_={
            "text": statement.excluded.text,
            "created_date": statement.excluded.created_date,
            "rubrics": statement.excluded.rubrics,
        },
    )
    async with engine.begin() as connection:
        await connection.execute(statement)


async def bulk_index_posts(
    es: AsyncElasticsearch, index_name: str, rows: list[PostRow]
) -> None:
    _, errors = await async_bulk(
        es,
        _es_actions(index_name, rows),
        raise_on_error=False,
        raise_on_exception=False,
    )
    if errors:
        raise RuntimeError(f"ошибки bulk-индексации: {errors[:3]}")
    await es.indices.refresh(index=index_name)
