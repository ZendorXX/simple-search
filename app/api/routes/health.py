from fastapi import APIRouter, Request, Response
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict:
    return {"status": "alive"}


@router.get(
    "/health/ready",
    summary="Проверка готовности",
    description="Возвращает 200, когда PostgreSQL и Elasticsearch доступны, иначе 503.",
    responses={503: {"description": "Одна из зависимостей недоступна"}},
)
async def ready(request: Request) -> Response:
    try:
        async with request.app.state.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        es_alive = await request.app.state.es.ping()
    except Exception:
        return Response(
            content='{"status":"not_ready"}',
            status_code=503,
            media_type="application/json",
        )
    if not es_alive:
        return Response(
            content='{"status":"not_ready"}',
            status_code=503,
            media_type="application/json",
        )
    return Response(
        content='{"status":"ready"}',
        status_code=200,
        media_type="application/json",
    )
