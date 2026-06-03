"""Reusable FastAPI dependencies (DB session + auth guards).

Routes import from here so that auth wiring (bearer extraction, token decode,
user lookup, role checks) stays in one place.
"""
from typing import Annotated

from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config.constants import UserRole
from app.config.security import decode_access_token
from app.config.settings import settings
from app.core.exceptions import AppException
from app.database.db import get_db
from app.database.models.user import User
from app.services import auth_service


# tokenUrl is only used by OpenAPI/Swagger's "Authorize" button.
# `auto_error=False` lets us emit our standardized error envelope instead of
# Starlette's default 401 plain dict.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


DBSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DBSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if not token:
        raise AppException(
            "Not authenticated",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="not_authenticated",
        )
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise AppException(
            "Invalid or expired token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_token",
        ) from exc

    subject = payload.get("sub")
    if subject is None:
        raise AppException(
            "Malformed token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_token",
        )

    user = auth_service.get_user_by_id(db, int(subject))
    if user is None:
        raise AppException(
            "User no longer exists",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="user_not_found",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN.value:
        raise AppException(
            "Admin privileges required",
            status_code=status.HTTP_403_FORBIDDEN,
            code="forbidden",
        )
    return user


def require_faculty_or_admin(user: CurrentUser) -> User:
    if user.role not in (UserRole.ADMIN.value, UserRole.FACULTY.value):
        raise AppException(
            "Faculty or admin privileges required",
            status_code=status.HTTP_403_FORBIDDEN,
            code="forbidden",
        )
    return user
