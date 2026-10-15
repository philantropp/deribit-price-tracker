from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.exception_handlers import register_exception_handlers
from app.api.routers import prices
from app.config import Settings, get_settings
from app.db.database import Database
from app.log_config import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory: `uvicorn app.api.main:create_app --factory`."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.database = Database(settings.database_url)
        try:
            yield
        finally:
            await app.state.database.dispose()

    app = FastAPI(
        title="Deribit Price Tracker",
        description="Index prices of BTC and ETH collected from Deribit every minute.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(prices.router, prefix="/api/v1")
    register_exception_handlers(app)

    @app.get("/health", tags=["service"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
