from elasticsearch import ApiError, AsyncElasticsearch
from sqlalchemy import delete

from app.models.post import Post


async def delete_post(
    es: AsyncElasticsearch,
    session_factory,
    index_name: str,
    post_id: int,
) -> None:
    async with session_factory() as session:
        await session.execute(delete(Post).where(Post.id == post_id))
        await session.commit()
    try:
        await es.delete(index=index_name, id=str(post_id))
    except ApiError as exc:
        if exc.status_code != 404:
            raise
