from fastapi import APIRouter, Request, Response

from app.api.errors import SERVICE_UNAVAILABLE_ERRORS, service_unavailable
from app.services.delete import delete_post
from app.settings import get_settings

router = APIRouter()


@router.delete(
    "/posts/{post_id}",
    status_code=204,
    summary="Удалить публикацию",
    description=(
        "Удаляет запись из PostgreSQL и документ из Elasticsearch по id. "
        "Операция идемпотентна: повторный DELETE безопасен. "
        "Недоступность Elasticsearch — 503; повторный запрос после "
        "восстановления доводит очистку индекса."
    ),
    responses={
        204: {"description": "Документ удалён из БД и индекса (в том числе повторно)"},
        503: {
            "description": "Сервис временно недоступен, запрос можно повторить",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"detail": {"type": "string"}}}
                }
            },
        },
    },
)
async def remove_post(post_id: int, request: Request) -> Response:
    settings = get_settings()
    try:
        await delete_post(
            request.app.state.es,
            request.app.state.session_factory,
            settings.es_index_name,
            post_id,
        )
    except SERVICE_UNAVAILABLE_ERRORS as exc:
        raise service_unavailable(
            "Сервис временно недоступен, повторите запрос позже"
        ) from exc
    return Response(status_code=204)
