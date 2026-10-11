import argparse
import asyncio
import json
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models.es import ensure_index, recreate_index
from app.models.post import Post
from app.repositories.db import create_engine
from app.repositories.es import create_es_client
from app.services.csv_reader import CsvValidationError, PostRow, parse_posts_csv
from app.services.storage import bulk_index_posts, upsert_posts
from app.settings import get_settings


@asynccontextmanager
async def storage() -> AsyncIterator[tuple[AsyncEngine, AsyncElasticsearch]]:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    es = create_es_client(settings.es_url)
    try:
        yield engine, es
    finally:
        await es.close()
        await engine.dispose()


async def import_csv(path: str) -> None:
    try:
        rows = parse_posts_csv(path)
    except CsvValidationError as exc:
        for error in exc.errors:
            print(error, file=sys.stderr)
        raise SystemExit(2) from None
    settings = get_settings()
    async with storage() as (engine, es):
        await ensure_index(es, settings.es_index_name)
        await upsert_posts(engine, rows)
        await bulk_index_posts(es, settings.es_index_name, rows)
    print(f"Импортировано записей: {len(rows)}")


async def reindex() -> None:
    settings = get_settings()
    async with storage() as (engine, es):
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Post))
            posts = result.scalars().all()
            rows = [
                PostRow(
                    id=post.id,
                    text=post.text,
                    created_date=post.created_date,
                    rubrics=post.rubrics,
                )
                for post in posts
            ]
        await recreate_index(es, settings.es_index_name)
        await bulk_index_posts(es, settings.es_index_name, rows)
    print(f"Проиндексировано записей: {len(rows)}")


def export_openapi(path: str) -> None:
    from app.main import app

    document = app.openapi()
    with open(path, "w", encoding="utf-8") as file:
        json.dump(document, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(f"OpenAPI записан в {path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser(
        "import-csv", help="Импорт публикаций из CSV в PostgreSQL и Elasticsearch"
    )
    import_parser.add_argument("path", help="Путь к CSV-файлу")

    subparsers.add_parser(
        "reindex", help="Полная переиндексация Elasticsearch из PostgreSQL"
    )

    openapi_parser = subparsers.add_parser(
        "export-openapi", help="Экспорт OpenAPI-схемы приложения в JSON-файл"
    )
    openapi_parser.add_argument("path", help="Путь для записи JSON-файла")

    args = parser.parse_args()
    if args.command == "import-csv":
        asyncio.run(import_csv(args.path))
    elif args.command == "reindex":
        asyncio.run(reindex())
    elif args.command == "export-openapi":
        export_openapi(args.path)


if __name__ == "__main__":
    main()
