"""Faculty ↔ class assignment service.

Manages the many-to-many relationship between faculty users and academic
classes.  Admin sets assignments; faculty can read their own.
"""
from __future__ import annotations

from typing import List

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.database.models.academic_class import AcademicClass
from app.database.models.faculty_class import FacultyClass
from app.database.models.user import User


logger = get_logger("attendai.faculty_classes")


def get_assignments(db: Session, user_id: int) -> List[dict]:
    """Return all class assignments for a faculty user.

    Each item: ``{"class_id": ..., "class_code": ...}``.
    """
    rows = db.execute(
        select(
            FacultyClass.class_id,
            AcademicClass.class_code,
            AcademicClass.major,
            AcademicClass.year,
            AcademicClass.section,
        )
        .join(AcademicClass, FacultyClass.class_id == AcademicClass.id)
        .where(FacultyClass.user_id == user_id)
        .order_by(AcademicClass.major, AcademicClass.year, AcademicClass.section)
    ).all()
    return [
        {
            "class_id": r[0],
            "class_code": r[1],
            "major": r[2],
            "year": r[3],
            "section": r[4],
        }
        for r in rows
    ]


def set_assignments(db: Session, user_id: int, class_ids: List[int]) -> List[dict]:
    """Replace the full set of class assignments for a faculty user.

    - Removes assignments not in `class_ids`.
    - Adds new assignments for class_ids not currently assigned.
    - Validates user is faculty and all class_ids exist + are active.

    Returns the new assignment list.
    """
    # Validate user is faculty.
    user = db.get(User, user_id)
    if user is None:
        raise AppException(
            "User not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="user_not_found",
        )
    if user.role == "admin":
        raise AppException(
            "Cannot assign classes to admin accounts",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="admin_not_assignable",
        )

    # Validate all class_ids exist and are active.
    if class_ids:
        classes = db.execute(
            select(AcademicClass).where(AcademicClass.id.in_(class_ids))
        ).scalars().all()
        found_ids = {c.id for c in classes}
        missing = set(class_ids) - found_ids
        if missing:
            raise AppException(
                f"Class IDs not found: {sorted(missing)}",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="invalid_class_ids",
            )
        inactive = [c.id for c in classes if not c.is_active]
        if inactive:
            raise AppException(
                f"Cannot assign inactive classes: {sorted(inactive)}",
                status_code=status.HTTP_400_BAD_REQUEST,
                code="inactive_class",
            )

    # Current assignments.
    current = db.execute(
        select(FacultyClass).where(FacultyClass.user_id == user_id)
    ).scalars().all()
    current_ids = {fc.class_id for fc in current}
    target_ids = set(class_ids)

    # Remove unneeded.
    to_remove = current_ids - target_ids
    if to_remove:
        for fc in current:
            if fc.class_id in to_remove:
                db.delete(fc)

    # Add new.
    to_add = target_ids - current_ids
    for cid in to_add:
        db.add(FacultyClass(user_id=user_id, class_id=cid))

    db.commit()

    removed = len(to_remove)
    added = len(to_add)
    if removed or added:
        logger.info(
            "Faculty assignments updated user_id=%s added=%d removed=%d total=%d",
            user_id, added, removed, len(target_ids),
        )

    return get_assignments(db, user_id)
