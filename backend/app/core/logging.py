"""Centralized logging configuration.

A single place that wires the stdlib `logging` module for the whole app:
- one stream handler with a readable, request-scoped format
- a `RequestIdFilter` that injects the current request's correlation ID
- a configurable level driven by `settings.LOG_LEVEL`

Business code calls `get_logger(__name__)`; it never configures logging itself.
"""
import logging
import sys
from contextvars import ContextVar

from app.config.settings import settings


# Context variable populated by RequestContextMiddleware for each request.
# Default "-" makes pre-request and background logs still render cleanly.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class _AsgiCancelFilter(logging.Filter):
    """Suppress noisy ASGI tracebacks from cancelled streaming responses.

    When a client disconnects from an MJPEG stream (or the server shuts
    down), uvicorn logs the CancelledError / connection-reset at ERROR
    level with a full traceback. This is expected operational behavior for
    long-lived streams, not an application error.
    """

    _NOISE_FRAGMENTS = ("CancelledError", "disconnect", "ASGI")

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info and record.exc_info[0] is not None:
            exc_name = record.exc_info[0].__name__
            if "Cancel" in exc_name or "Disconnect" in exc_name:
                return False
        msg = record.getMessage()
        if "CancelledError" in msg:
            return False
        return True


_LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def configure_logging() -> None:
    """Idempotent setup. Safe to call once at startup."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Uvicorn's access log duplicates what RequestContextMiddleware already emits.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(level)

    # Suppress noisy ASGI cancellation tracebacks from long-lived streaming
    # responses (MJPEG preview). These are expected on client disconnect and
    # server shutdown — not application errors.
    logging.getLogger("uvicorn.error").addFilter(_AsgiCancelFilter())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
