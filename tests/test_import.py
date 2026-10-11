import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.repositories.db import create_engine
from app.repositories.es import create_es_client
from app.services.csv_reader import CsvValidationError, parse_posts_csv
from app.settings import get_settings


async def _count_posts() -> int:
    engine = create_engine(get_settings().database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(select(func.count()).select_from(Post))
            return int(result.scalar_one())
    finally:
        await engine.dispose()


async def test_import_full_csv_and_idempotent_reimport() -> None:
    from app.cli.__main__ import import_csv

    await import_csv("/data/posts.csv")
    assert await _count_posts() == 1500

    await import_csv("/data/posts.csv")
    assert await _count_posts() == 1500

    engine = create_engine(get_settings().database_url)
    try:
        async with AsyncSession(engine) as session:
            row = (
                await session.execute(select(Post).where(Post.id == 1))
            ).scalar_one()
    finally:
        await engine.dispose()
    assert isinstance(row.rubrics, list)
    assert all(isinstance(item, str) for item in row.rubrics)
    assert "\n" in row.text

    es = create_es_client(get_settings().es_url)
    try:
        count = await es.count(index=get_settings().es_index_name)
    finally:
        await es.close()
    assert count["count"] == 1500


async def test_import_invalid_csv_reports_line_number(tmp_path) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text(
        "text,created_date,rubrics\n"
        "текст,2019-13-99 99:99:99,'[\"a\"]'\n",
        encoding="utf-8",
    )
    with pytest.raises(CsvValidationError) as exc_info:
        parse_posts_csv(str(bad_csv))
    assert any("строка 2" in error for error in exc_info.value.errors)


async def test_import_rejects_non_list_rubrics(tmp_path) -> None:
    bad_csv = tmp_path / "bad_rubrics.csv"
    bad_csv.write_text(
        "text,created_date,rubrics\n"
        "текст,2019-07-25 12:42:13,'VK-1'\n",
        encoding="utf-8",
    )
    with pytest.raises(CsvValidationError) as exc_info:
        parse_posts_csv(str(bad_csv))
    assert any("строка 2" in error for error in exc_info.value.errors)
