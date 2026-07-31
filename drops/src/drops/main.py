"""Application entry point and FastAPI factory for Drops service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from drops.api.error_handlers import drops_error_handler
from drops.api.routes import admin, drops, health, metrics
from drops.config import get_settings
from drops.domain.exceptions import DropError
from drops.infrastructure.database import engine
from drops.observability import (
    request_observability_middleware,
    setup_metrics,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage application-wide resources."""
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_metrics()
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )

    app.add_exception_handler(DropError, drops_error_handler)  # type: ignore[arg-type]

    app.middleware("http")(request_observability_middleware)

    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(drops.router)
    app.include_router(admin.router)

    return app


app = create_app()
