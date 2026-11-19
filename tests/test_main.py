"""Entry point: python -m booking."""

from typing import Any

import pytest

from booking import __main__ as entry


def test_main_starts_server_on_port_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setattr(entry.uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs))

    entry.main()

    assert calls == [
        {"factory": True, "host": "0.0.0.0", "port": 9090, "log_config": None},
    ]
