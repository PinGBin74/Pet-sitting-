"""NFR-03: every log line is a JSON object with timestamp, level, event, request_id."""

import io
import json
import logging
from typing import Any

import structlog

from booking.logging import MASK, REQUIRED_FIELDS, configure_logging


def parse_lines(stream: io.StringIO) -> list[dict[str, Any]]:
    """The NFR-03 check: every line must parse as JSON on its own."""
    return [json.loads(line) for line in stream.getvalue().splitlines()]


def test_structlog_record_is_json_with_required_fields() -> None:
    stream = io.StringIO()
    configure_logging("info", stream)

    structlog.get_logger("booking.test").info("booking.requested", booking_id="b-1")

    [record] = parse_lines(stream)
    assert set(REQUIRED_FIELDS) <= record.keys()
    assert record["event"] == "booking.requested"
    assert record["level"] == "info"
    assert record["booking_id"] == "b-1"
    assert record["timestamp"].endswith("Z")


def test_standard_library_record_is_json_too() -> None:
    stream = io.StringIO()
    configure_logging("info", stream)

    logging.getLogger("uvicorn.error").info("Started server process [%d]", 42)

    [record] = parse_lines(stream)
    assert set(REQUIRED_FIELDS) <= record.keys()
    assert record["event"] == "Started server process [42]"
    assert record["logger"] == "uvicorn.error"


def test_record_outside_a_request_has_null_request_id() -> None:
    stream = io.StringIO()
    configure_logging("info", stream)

    structlog.get_logger().info("service.started")

    [record] = parse_lines(stream)
    assert record["request_id"] is None


def test_bound_request_id_reaches_every_record() -> None:
    stream = io.StringIO()
    configure_logging("info", stream)

    with structlog.contextvars.bound_contextvars(request_id="abc"):
        structlog.get_logger().info("first")
        logging.getLogger("library").warning("second")

    assert [r["request_id"] for r in parse_lines(stream)] == ["abc", "abc"]


def test_sensitive_values_are_masked() -> None:
    stream = io.StringIO()
    configure_logging("info", stream)

    structlog.get_logger().info(
        "user.login",
        user_id="u-1",
        password="hunter2",
        access_token="eyJ...",
        Email="owner@example.com",
        phone="+79990000000",
    )

    [record] = parse_lines(stream)
    assert record["user_id"] == "u-1"
    assert record["password"] == MASK
    assert record["access_token"] == MASK
    assert record["Email"] == MASK
    assert record["phone"] == MASK


def test_records_below_level_are_dropped() -> None:
    stream = io.StringIO()
    configure_logging("warning", stream)

    structlog.get_logger().info("hidden")
    logging.getLogger("library").info("hidden too")
    structlog.get_logger().warning("shown")

    assert [r["event"] for r in parse_lines(stream)] == ["shown"]


def test_exception_is_rendered_inside_the_json_line() -> None:
    stream = io.StringIO()
    configure_logging("info", stream)

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        structlog.get_logger().exception("request.failed")

    [record] = parse_lines(stream)
    assert record["level"] == "error"
    assert "RuntimeError: boom" in record["exception"]


def test_reconfiguring_does_not_duplicate_lines() -> None:
    stream = io.StringIO()
    configure_logging("info", io.StringIO())
    configure_logging("info", stream)

    structlog.get_logger().info("once")

    assert len(parse_lines(stream)) == 1
