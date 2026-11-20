"""Entry point: python -m booking."""

from typing import Any

import pytest

from booking import __main__ as entry
from src.booking.config import get_settings


def test_main_starts_server_on_port_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setattr(entry.uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs))

    entry.main()

    assert calls == [
        {"factory": True, "host": "0.0.0.0", "port": 9090, "log_config": None},
    ]


def test_main_stops_with_readable_message_when_configuration_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "mysql://user:s3cret@db/app")
    monkeypatch.setattr(entry.uvicorn, "run", lambda *args, **kwargs: None)

    get_settings.cache_clear()

    with pytest.raises(SystemExit) as stopped:
        entry.main()

    message = str(stopped.value)
    assert "DATABASE_URL" in message
    assert "s3cret" not in message
