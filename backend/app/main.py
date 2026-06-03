"""FastAPI application bootstrap."""
from fastapi import FastAPI

from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.middleware import register_middleware
from app.routes import api_router, health


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    register_middleware(app)
    register_exception_handlers(app)

    # Unversioned health endpoint (used by Electron/process supervisors).
    app.include_router(health.router)

    # Versioned API.
    app.include_router(api_router)

    return app


app = create_app()
