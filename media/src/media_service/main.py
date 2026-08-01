"""FastAPI application factory for Media."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from media_service.api.dependencies import get_verifier
from media_service.api.error_handlers import media_error_handler
from media_service.api.routes import assets, health, metrics
from media_service.config import get_settings
from media_service.domain.exceptions import MediaError
from media_service.infrastructure.database import engine
from media_service.observability import request_observability_middleware, setup_observability


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_verifier().validate_startup()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_observability()
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
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    app.add_exception_handler(MediaError, media_error_handler)  # type: ignore[arg-type]
    app.middleware("http")(request_observability_middleware)
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(assets.router)
    return app


app = create_app()
