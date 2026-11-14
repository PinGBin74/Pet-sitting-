"""Application factory.

Skeleton: settings (config.py), structured logging (logging.py) and the
request-id middleware are added in the next steps of lab 3A.
"""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness answer. Deliberately free of external dependencies."""

    status: Literal["ok"] = "ok"


def create_app() -> FastAPI:
    """Build the application."""
    app = FastAPI(title="Pet-sitting API", version="0.1.0")

    @app.get("/health", response_model=HealthResponse, summary="Liveness probe")
    async def health() -> HealthResponse:
        """Report that the process is alive; touches no external system."""
        return HealthResponse()

    return app
