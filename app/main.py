import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, posts, search
from app.models.es import ensure_index
from app.repositories.db import create_engine, create_session_factory
from app.repositories.es import create_es_client
from app.settings import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_settings()
        engine = create_engine(settings.database_url)
        es_client = create_es_client(settings.es_url)
        app.state.engine = engine
        app.state.es = es_client
        app.state.session_factory = create_session_factory(engine)
        try:
            await ensure_index(es_client, settings.es_index_name)
        except Exception:
            logger.warning("Не удалось создать индекс при старте; /health/ready сообщит о готовности")
        yield
        await es_client.close()
        await engine.dispose()

    app = FastAPI(
        title="Simple Search API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(search.router)
    app.include_router(posts.router)
    return app


app = create_app()
