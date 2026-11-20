"""Application factory."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from booking.api.middleware import RequestIdMiddleware
from booking.config import Settings, get_settings
from booking.logging import configure_logging


class HealthResponse(BaseModel):
    """Liveness answer. Deliberately free of external dependencies."""

    status: Literal["ok"] = "ok"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application; settings are read from the environment if not given."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Pet-sitting API", version=settings.app_version)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/health", response_model=HealthResponse, summary="Liveness probe")
    async def health() -> HealthResponse:
        """Report that the process is alive; touches no external system."""
        return HealthResponse()

    return app
