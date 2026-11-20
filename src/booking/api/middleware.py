"""Request identifier for every HTTP call (NFR-03).

The identifier is taken from the `X-Request-ID` header when it is safe, or
generated otherwise. It is bound to every log record of the request and is
returned in the response header, including on unhandled errors.
"""

import re
import time
from uuid import uuid4

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"

# A client value goes into the log as is: allow only a short, plain token so it
# cannot inject line breaks or fake JSON fields.
_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")

logger = structlog.get_logger(__name__)


def resolve_request_id(incoming: str | None) -> str:
    """Keep a safe incoming identifier; otherwise generate a new one."""
    if incoming is not None and _SAFE_REQUEST_ID.fullmatch(incoming):
        return incoming
    return uuid4().hex


class RequestIdMiddleware:
    """Pure ASGI middleware: no response buffering, works for streaming too."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = resolve_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))
        status_code = 500
        response_started = False
        started_at = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        with structlog.contextvars.bound_contextvars(request_id=request_id):
            try:
                await self.app(scope, receive, send_with_request_id)
            except Exception:
                logger.exception("request.failed", method=scope["method"], path=scope["path"])
                if response_started:
                    raise
                # Answer here, not in Starlette's outer error handler: that one
                # would send the 500 without the identifier.
                response = JSONResponse(
                    {"detail": "Internal Server Error"},
                    status_code=500,
                    headers={REQUEST_ID_HEADER: request_id},
                )
                await response(scope, receive, send)
                status_code = 500

            logger.info(
                "request.completed",
                method=scope["method"],
                path=scope["path"],
                status=status_code,
                duration_ms=round((time.perf_counter() - started_at) * 1000, 1),
            )
