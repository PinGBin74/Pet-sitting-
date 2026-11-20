"""Application factory."""

from fastapi import FastAPI

from booking.api import system
from booking.api.middleware import RequestIdMiddleware
from booking.config import Settings, get_settings
from booking.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application; settings are read from the environment if not given."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Pet-sitting API", version=settings.app_version)
    app.dependency_overrides[get_settings] = lambda: settings
    app.add_middleware(RequestIdMiddleware)
    app.include_router(system.router)

    return app
