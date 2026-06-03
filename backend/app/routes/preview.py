"""MJPEG preview stream endpoint.

Serves annotated recognition frames as a multipart/x-mixed-replace stream.
Designed for localhost ``<img src>`` consumption — not internet-scale streaming.

Auth note: ``<img src>`` cannot send Authorization headers, so this endpoint
also accepts the JWT via a ``token`` query parameter.  The router-level
``require_faculty_or_admin`` dependency is omitted; auth is checked inline.
"""
from __future__ import annotations

import time
from typing import Generator, Optional

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import Response, StreamingResponse

from app.config.constants import UserRole
from app.config.security import decode_access_token
from app.config.settings import settings
from app.core.exceptions import AppException
from app.recognition.preview_buffer import PreviewBuffer


router = APIRouter(
    prefix="/preview",
    tags=["Recognition"],
)

_BOUNDARY = b"frame"
_CONTENT_TYPE = f"multipart/x-mixed-replace; boundary={_BOUNDARY.decode()}"


def _authenticate_stream(request: Request, token: Optional[str]) -> None:
    """Validate JWT from query param or Authorization header."""
    # Try query param first (for <img src>), then fall back to header.
    jwt = token
    if not jwt:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            jwt = auth_header[7:]
    if not jwt:
        raise AppException(
            "Not authenticated",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="not_authenticated",
        )
    try:
        payload = decode_access_token(jwt)
    except ValueError as exc:
        raise AppException(
            "Invalid or expired token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_token",
        ) from exc

    subject = payload.get("sub")
    role = payload.get("role", "")
    if subject is None:
        raise AppException("Malformed token", status_code=status.HTTP_401_UNAUTHORIZED, code="invalid_token")
    if role not in (UserRole.ADMIN.value, UserRole.FACULTY.value):
        raise AppException("Insufficient privileges", status_code=status.HTTP_403_FORBIDDEN, code="forbidden")


def _mjpeg_generator(buf: PreviewBuffer) -> Generator[bytes, None, None]:
    """Yield MJPEG frames until the client disconnects or the server shuts down.

    Catches GeneratorExit (client disconnect / ASGI cancellation) so
    shutdown doesn't produce noisy traceback spam.  Exits promptly when
    the buffer is shut down (``buf.is_shutdown``).
    """
    min_interval = 1.0 / settings.PREVIEW_MAX_FPS
    try:
        while not buf.is_shutdown:
            jpeg = buf.wait(timeout=0.5)
            if jpeg is None:
                continue
            yield (
                b"--" + _BOUNDARY + b"\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n"
                b"\r\n" + jpeg + b"\r\n"
            )
            time.sleep(min_interval)
    except GeneratorExit:
        return


@router.get("/stream")
async def preview_stream(
    request: Request,
    token: Optional[str] = Query(default=None),
):
    _authenticate_stream(request, token)

    buf: PreviewBuffer | None = getattr(request.app.state, "preview_buffer", None)
    if buf is None or buf.latest() is None:
        return Response(status_code=204)

    return StreamingResponse(
        _mjpeg_generator(buf),
        media_type=_CONTENT_TYPE,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
        },
    )
