from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from auth_service.api import (
    admin,
    audit,
    auth,
    health,
    metrics,
    sessions,
    users,
    well_known,
)
from auth_service.api.error_handlers import application_error_handler
from auth_service.application.errors import ApplicationError
from auth_service.cache import redis_client
from auth_service.config import get_settings
from auth_service.database import engine
from auth_service.key_management import validate_configured_key_pair
from auth_service.observability import request_observability_middleware


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage application resources for its lifetime."""
    yield
    await redis_client.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    validate_configured_key_pair()
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

    app.middleware("http")(request_observability_middleware)
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(well_known.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(sessions.router)
    app.include_router(admin.router)
    app.include_router(audit.router)
    return app


app = create_app()
