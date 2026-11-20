"""Structured JSON log (NFR-03).

Every record is one JSON object per line with at least `timestamp`, `level`,
`event` and `request_id`. Records from the standard library (uvicorn and other
libraries) pass through the same chain, so the rule holds for 100 % of lines.
Sensitive fields are masked before rendering.
"""

import logging
import sys
from typing import TextIO

import structlog
from structlog.types import EventDict, Processor, WrappedLogger

REQUIRED_FIELDS = ("timestamp", "level", "event", "request_id")

# Keys whose values must never reach the log (NFR-03, overview.md «Защищённость»).
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "secret",
        "email",
        "phone",
        "database_url",
    }
)
MASK = "***"

_HANDLER_MARK = "_booking_json_handler"


def _ensure_request_id(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Records outside an HTTP request (startup, background work) carry null."""
    event_dict.setdefault("request_id", None)
    return event_dict


def _mask_sensitive(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    for key in event_dict:
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = MASK
    return event_dict


def _shared_processors() -> list[Processor]:
    """Applied both to structlog calls and to standard library records."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        _ensure_request_id,
        _mask_sensitive,
    ]


def configure_logging(level: str = "info", stream: TextIO | None = None) -> None:
    """Route all logging to one JSON handler. Safe to call more than once."""
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_shared_processors(),
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(formatter)
    setattr(handler, _HANDLER_MARK, True)

    root = logging.getLogger()
    for old in [h for h in root.handlers if getattr(h, _HANDLER_MARK, False)]:
        root.removeHandler(old)
    root.addHandler(handler)
    root.setLevel(level.upper())

    # The request-id middleware writes one record per request; uvicorn's own
    # access line would duplicate it and add the client address.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *_shared_processors(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
