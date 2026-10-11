from elasticsearch import AsyncElasticsearch


def create_es_client(es_url: str) -> AsyncElasticsearch:
    return AsyncElasticsearch(es_url)
