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
    from src.booking.config import ConfigurationError

    def fake_get_settings() -> None:
        raise ConfigurationError("Invalid configuration: DATABASE_URL")

    monkeypatch.setattr("booking.__main__.get_settings", fake_get_settings)
    monkeypatch.setattr(entry.uvicorn, "run", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit) as stopped:
        entry.main()

    message = str(stopped.value)
    assert "DATABASE_URL" in message
    assert "s3cret" not in message
