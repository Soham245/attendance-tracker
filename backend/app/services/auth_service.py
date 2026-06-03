"""Authentication service.

All credential checks, user lookups, and token orchestration live here so
routes stay thin and dependencies stay focused on FastAPI plumbing.
"""
from typing import Optional, Tuple

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.security import create_access_token, hash_password, verify_password
from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.database.models.user import User
from app.database.schemas.auth_schema import TokenData


logger = get_logger("attendai.auth")


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def authenticate_user(db: Session, username: str, password: str) -> User:
    user = get_user_by_username(db, username)
    if user is None or not verify_password(password, user.password_hash):
        logger.info("Failed login attempt for username=%s", username)
        raise AppException(
            "Invalid username or password",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_credentials",
        )
    if not user.is_active:
        logger.info("Login attempt by deactivated user username=%s", username)
        raise AppException(
            "Account is deactivated. Contact an administrator.",
            status_code=status.HTTP_403_FORBIDDEN,
            code="account_deactivated",
        )
    return user


def issue_token(user: User) -> TokenData:
    return TokenData(
        access_token=create_access_token(user_id=user.id, role=user.role),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        must_change_password=user.must_change_password,
    )


def login(db: Session, username: str, password: str) -> Tuple[User, TokenData]:
    user = authenticate_user(db, username, password)
    token = issue_token(user)
    logger.info("User %s (role=%s) logged in", user.username, user.role)
    return user, token


def change_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> User:
    """Change the user's own password after verifying current password."""
    if not verify_password(current_password, user.password_hash):
        raise AppException(
            "Current password is incorrect",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="wrong_password",
        )
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()
    db.refresh(user)
    logger.info("User %s changed their password", user.username)
    return user
