"""HTTP middleware registration.

Two middlewares are mounted:
- `CORSMiddleware` — Electron renderer + localhost dev origins.
- `RequestContextMiddleware` — assigns/propagates a correlation ID, times the
  request, and emits a single structured access log line per response.

`RequestContextMiddleware` is implemented as pure ASGI middleware (not
Starlette's `BaseHTTPMiddleware`) so that streaming responses (MJPEG
preview) pass through without being wrapped in AnyIO memory streams.
This eliminates noisy `CancelledError` tracebacks on client disconnect
and server shutdown.
"""
import time
import uuid
from typing import Any, Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config.settings import settings
from app.core.logging import get_logger, request_id_ctx


REQUEST_ID_HEADER = "X-Request-ID"

_access_logger = get_logger("attendai.access")


class RequestContextMiddleware:
    """Pure ASGI middleware: correlation ID + request timing + access log.

    Accepts an inbound `X-Request-ID` header (useful when Electron forwards
    one) and falls back to a fresh hex UUID. The ID is exposed via
    `request_id_ctx` so the logging filter can stamp every log line emitted
    during the request, and echoed back in the response header.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        rid = (
            headers.get(REQUEST_ID_HEADER.lower().encode(), b"").decode()
            or uuid.uuid4().hex
        )
        token = request_id_ctx.set(rid)
        start = time.perf_counter()
        status_code: int | None = None

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                raw_headers: list = list(message.get("headers") or [])
                raw_headers.append(
                    (REQUEST_ID_HEADER.lower().encode(), rid.encode())
                )
                message = {**message, "headers": raw_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            method = scope.get("method", "?")
            path = scope.get("path", "?")
            _access_logger.exception(
                "%s %s -> 500 (%.2fms)", method, path, elapsed_ms
            )
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            method = scope.get("method", "?")
            path = scope.get("path", "?")
            if status_code is not None:
                _access_logger.info(
                    "%s %s -> %s (%.2fms)",
                    method, path, status_code, elapsed_ms,
                )
            request_id_ctx.reset(token)


def register_middleware(app: FastAPI) -> None:
    # CORS first so preflights are answered before custom middleware runs.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(RequestContextMiddleware)
