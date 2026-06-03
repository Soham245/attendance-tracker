"""User management service — admin-only CRUD for faculty accounts.

VisionAttend enforces a single-admin model: exactly one admin (the system
owner) exists. All other accounts are faculty operators. The service
layer rejects any attempt to create, promote, deactivate, or delete
admin accounts — regardless of what the caller requests.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.constants import UserRole
from app.config.security import hash_password
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.database.models.user import User


logger = get_logger("attendai.users")


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def _require_faculty(user: User, action: str = "modify") -> None:
    """Reject any mutation targeting the admin account."""
    if user.role == UserRole.ADMIN.value:
        raise AppException(
            f"Cannot {action} the admin account",
            status_code=status.HTTP_403_FORBIDDEN,
            code="admin_protected",
        )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def list_users(
    db: Session,
    *,
    role: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[User], int]:
    """Return paginated user list, optionally filtered by role."""
    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)

    if role is not None:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)

    total = db.scalar(count_stmt) or 0
    items = (
        db.execute(stmt.order_by(User.created_at.desc()).offset(skip).limit(limit))
        .scalars()
        .all()
    )
    return list(items), total


def get_user(db: Session, user_id: int) -> User:
    """Fetch a single user by ID or raise 404."""
    user = db.get(User, user_id)
    if user is None:
        raise AppException(
            "User not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="user_not_found",
        )
    return user


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def create_faculty(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
) -> User:
    """Create a new faculty user. Raises on duplicate username/email."""
    # Check duplicates.
    existing = db.execute(
        select(User).where((User.username == username) | (User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        field = "username" if existing.username == username else "email"
        raise AppException(
            f"A user with this {field} already exists",
            status_code=status.HTTP_409_CONFLICT,
            code="user_duplicate",
        )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=UserRole.FACULTY.value,
        is_active=True,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Created faculty user: %s (id=%d)", username, user.id)
    return user


def update_faculty(
    db: Session,
    user_id: int,
    *,
    username: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
) -> User:
    """Update a faculty user's profile. Admin accounts cannot be edited."""
    user = get_user(db, user_id)
    _require_faculty(user, "edit")

    # Check for duplicate username/email against *other* users.
    if username is not None and username != user.username:
        dup = db.execute(
            select(User).where(User.username == username, User.id != user_id)
        ).scalar_one_or_none()
        if dup:
            raise AppException(
                "A user with this username already exists",
                status_code=status.HTTP_409_CONFLICT,
                code="user_duplicate",
            )
        user.username = username

    if email is not None and email != user.email:
        dup = db.execute(
            select(User).where(User.email == email, User.id != user_id)
        ).scalar_one_or_none()
        if dup:
            raise AppException(
                "A user with this email already exists",
                status_code=status.HTTP_409_CONFLICT,
                code="user_duplicate",
            )
        user.email = email

    if password is not None:
        user.password_hash = hash_password(password)

    db.commit()
    db.refresh(user)
    logger.info("Updated faculty user: %s (id=%d)", user.username, user.id)
    return user


def toggle_active(db: Session, user_id: int, *, active: bool) -> User:
    """Activate or deactivate a faculty user. Admin cannot be deactivated."""
    user = get_user(db, user_id)
    if not active:
        _require_faculty(user, "deactivate")
    user.is_active = active
    db.commit()
    db.refresh(user)
    action = "activated" if active else "deactivated"
    logger.info("User %s (id=%d) %s", user.username, user.id, action)
    return user


def reset_password(db: Session, user_id: int, *, new_password: str) -> User:
    """Admin resets a faculty user's password and forces change on next login."""
    user = get_user(db, user_id)
    _require_faculty(user, "reset password for")
    user.password_hash = hash_password(new_password)
    user.must_change_password = True
    db.commit()
    db.refresh(user)
    logger.info("Admin reset password for user: %s (id=%d)", user.username, user.id)
    return user


def delete_faculty(db: Session, user_id: int) -> None:
    """Permanently delete a faculty account. Admin cannot be deleted."""
    user = get_user(db, user_id)
    _require_faculty(user, "delete")
    db.delete(user)
    db.commit()
    logger.info("Deleted faculty user: %s (id=%d)", user.username, user_id)
