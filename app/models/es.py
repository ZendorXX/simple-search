POSTS_INDEX_BODY: dict = {
    "mappings": {
        "properties": {
            "id": {"type": "long"},
            "text": {
                "type": "text",
                "analyzer": "russian",
                "fields": {
                    "standard": {"type": "text", "analyzer": "standard"},
                },
            },
            "created_date": {
                "type": "date",
                "format": "yyyy-MM-dd HH:mm:ss||strict_date_optional_time||epoch_millis",
            },
        }
    }
}


async def ensure_index(client, index_name: str) -> None:
    exists = await client.indices.exists(index=index_name)
    if not exists:
        await client.indices.create(index=index_name, body=POSTS_INDEX_BODY)


async def recreate_index(client, index_name: str) -> None:
    if await client.indices.exists(index=index_name):
        await client.indices.delete(index=index_name)
    await client.indices.create(index=index_name, body=POSTS_INDEX_BODY)
