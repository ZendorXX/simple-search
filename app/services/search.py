from sqlalchemy import select
from elasticsearch import AsyncElasticsearch

from app.models.post import Post

SEARCH_LIMIT = 20


async def search_posts(
    es: AsyncElasticsearch,
    session_factory,
    index_name: str,
    query: str,
) -> list[Post]:
    items: list[Post] = []
    search_after = None
    while len(items) < SEARCH_LIMIT:
        body: dict = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["text", "text.standard"],
                    "operator": "or",
                }
            },
            "sort": [
                {"created_date": {"order": "desc"}},
                {"id": {"order": "asc"}},
            ],
            "size": SEARCH_LIMIT,
        }
        if search_after is not None:
            body["search_after"] = search_after
        response = await es.search(index=index_name, body=body)
        hits = response["hits"]["hits"]
        if not hits:
            break
        wanted_ids = [int(hit["_id"]) for hit in hits]
        async with session_factory() as session:
            result = await session.execute(
                select(Post).where(Post.id.in_(wanted_ids))
            )
            found = {post.id: post for post in result.scalars()}
        for hit in hits:
            post = found.get(int(hit["_id"]))
            if post is not None:
                items.append(post)
                if len(items) == SEARCH_LIMIT:
                    break
        search_after = hits[-1]["sort"]
        if len(hits) < SEARCH_LIMIT:
            break
    return items
