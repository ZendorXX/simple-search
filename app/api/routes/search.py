from fastapi import APIRouter, Request

from app.api.errors import SERVICE_UNAVAILABLE_ERRORS, service_unavailable
from app.api.schemas import SearchRequest, SearchResponse
from app.services.search import search_posts
from app.settings import get_settings

router = APIRouter()


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Поиск публикаций по тексту",
    description=(
        "Ищет документы по тексту запроса (OR-семантика токенов), возвращает "
        "до 20 записей со всеми полями, сначала новые. Пустой запрос — 422, "
        "недоступность PostgreSQL или Elasticsearch — 503."
    ),
    responses={
        503: {
            "description": "PostgreSQL или Elasticsearch временно недоступны",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"detail": {"type": "string"}}}
                }
            },
        }
    },
)
async def search(payload: SearchRequest, request: Request) -> SearchResponse:
    settings = get_settings()
    try:
        items = await search_posts(
            request.app.state.es,
            request.app.state.session_factory,
            settings.es_index_name,
            payload.query,
        )
    except SERVICE_UNAVAILABLE_ERRORS as exc:
        raise service_unavailable("Поисковый сервис временно недоступен") from exc
    return SearchResponse(items=items)
