"""Shared fixtures: a valid environment and a clean logging setup for every test."""

import logging
from collections.abc import Iterator

import pytest

from booking.config import get_settings

TEST_DATABASE_URL = "postgresql://test:test@localhost:5432/test"


@pytest.fixture(autouse=True)
def _environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """DATABASE_URL is required; settings are cached per process, so reset them."""
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _detach_log_handlers() -> Iterator[None]:
    """configure_logging() binds a handler to the current stdout; pytest closes it."""
    yield
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, "_booking_json_handler", False)]:
        root.removeHandler(handler)
