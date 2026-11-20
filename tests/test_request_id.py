"""Request identifier: returned in the response and present in every log record."""

import io
import json
from typing import Any

import pytest
import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient

from booking.api.middleware import REQUEST_ID_HEADER, RequestIdMiddleware, resolve_request_id
from booking.logging import REQUIRED_FIELDS, configure_logging


def make_client(stream: io.StringIO) -> TestClient:
    configure_logging("info", stream)
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/work")
    async def work() -> dict[str, str]:
        structlog.get_logger().info("work.done")
        return {"ok": "yes"}

    @app.get("/sync-work")
    def sync_work() -> dict[str, str]:  # runs in a worker thread
        structlog.get_logger().info("sync.done")
        return {"ok": "yes"}

    @app.get("/broken")
    async def broken() -> None:
        raise RuntimeError("boom")

    return TestClient(app)


def records(stream: io.StringIO) -> list[dict[str, Any]]:
    """Server-side records; the test client's own `httpx` line is not part of the request."""
    parsed = [json.loads(line) for line in stream.getvalue().splitlines()]
    return [record for record in parsed if not str(record.get("logger")).startswith("httpx")]


def test_response_carries_generated_request_id() -> None:
    client = make_client(io.StringIO())

    response = client.get("/work")

    assert response.status_code == 200
    assert len(response.headers[REQUEST_ID_HEADER]) == 32


@pytest.mark.parametrize("path", ["/work", "/sync-work"])
def test_every_record_of_the_request_has_the_returned_id(path: str) -> None:
    stream = io.StringIO()
    client = make_client(stream)

    response = client.get(path)

    lines = records(stream)
    assert len(lines) == 2  # handler record + request.completed
    assert all(set(REQUIRED_FIELDS) <= line.keys() for line in lines)
    assert {line["request_id"] for line in lines} == {response.headers[REQUEST_ID_HEADER]}


def test_completed_record_describes_the_request() -> None:
    stream = io.StringIO()
    client = make_client(stream)

    client.get("/work")

    completed = records(stream)[-1]
    assert completed["event"] == "request.completed"
    assert completed["method"] == "GET"
    assert completed["path"] == "/work"
    assert completed["status"] == 200
    assert completed["duration_ms"] >= 0


def test_safe_incoming_id_is_kept() -> None:
    client = make_client(io.StringIO())

    response = client.get("/work", headers={REQUEST_ID_HEADER: "web-7f3a.1"})

    assert response.headers[REQUEST_ID_HEADER] == "web-7f3a.1"


def test_two_requests_get_different_ids() -> None:
    client = make_client(io.StringIO())

    first = client.get("/work").headers[REQUEST_ID_HEADER]
    second = client.get("/work").headers[REQUEST_ID_HEADER]

    assert first != second


def test_unknown_path_still_gets_an_id() -> None:
    stream = io.StringIO()
    client = make_client(stream)

    response = client.get("/missing")

    assert response.status_code == 404
    assert records(stream)[-1]["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_unhandled_error_returns_500_with_id_and_logs_it() -> None:
    stream = io.StringIO()
    client = make_client(stream)

    response = client.get("/broken")

    request_id = response.headers[REQUEST_ID_HEADER]
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    failed, completed = records(stream)
    assert failed["event"] == "request.failed"
    assert "RuntimeError: boom" in failed["exception"]
    assert failed["request_id"] == completed["request_id"] == request_id
    assert completed["status"] == 500


def test_request_id_is_not_left_in_context_after_request() -> None:
    stream = io.StringIO()
    client = make_client(stream)
    client.get("/work")

    structlog.get_logger().info("after")

    assert records(stream)[-1]["request_id"] is None


@pytest.mark.parametrize(
    "incoming",
    [
        "",
        "a" * 65,
        "bad id with spaces",
        'x", "level": "fake',
        "line\nbreak",
    ],
)
def test_unsafe_incoming_id_is_replaced(incoming: str) -> None:
    resolved = resolve_request_id(incoming)

    assert resolved != incoming
    assert len(resolved) == 32
