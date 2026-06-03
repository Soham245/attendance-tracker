"""Centralized application exception + global handlers."""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.database.schemas.response import ErrorDetail, ErrorResponse


logger = get_logger("attendai.exceptions")


class AppException(Exception):
    """Base class for domain-level exceptions raised by services/routes."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "app_error",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _json(status_code: int, payload: ErrorResponse) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=payload.model_dump(exclude_none=True))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def _app_exc(_: Request, exc: AppException) -> JSONResponse:
        return _json(
            exc.status_code,
            ErrorResponse(
                message=exc.message,
                errors=[ErrorDetail(code=exc.code, message=exc.message)],
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return _json(
            exc.status_code,
            ErrorResponse(
                message=message,
                errors=[ErrorDetail(code=f"http_{exc.status_code}", message=message)],
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            ErrorDetail(
                code="validation_error",
                message=err.get("msg", "Invalid input"),
                field=".".join(str(p) for p in err.get("loc", []) if p != "body"),
            )
            for err in exc.errors()
        ]
        return _json(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorResponse(message="Request validation failed", errors=details),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_exc(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Unhandled database error: %s", exc)
        return _json(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                message="Database error",
                errors=[ErrorDetail(code="database_error", message="Database error")],
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled_exc(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return _json(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                message="Internal server error",
                errors=[ErrorDetail(code="internal_error", message="Internal server error")],
            ),
        )
