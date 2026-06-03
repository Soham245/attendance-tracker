"""Academic class CRUD — admin only.

Manages the AcademicClass entity: create, update, deactivate, and
safe-delete (refuses when students are still assigned).
"""
from typing import List, Tuple

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.database.models.academic_class import AcademicClass
from app.database.models.faculty_class import FacultyClass
from app.database.models.student import Student
from app.database.models.user import User
from app.database.schemas.class_schema import (
    ClassCreate,
    ClassUpdate,
    generate_class_code,
)


logger = get_logger("attendai.classes")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_code_available(
    db: Session, class_code: str, exclude_id: int | None = None
) -> None:
    stmt = select(AcademicClass.id).where(AcademicClass.class_code == class_code)
    if exclude_id is not None:
        stmt = stmt.where(AcademicClass.id != exclude_id)
    if db.execute(stmt).first() is not None:
        raise AppException(
            f"Class code '{class_code}' already exists",
            status_code=status.HTTP_409_CONFLICT,
            code="duplicate_class_code",
        )


def _assert_natural_key_available(
    db: Session,
    major: str,
    year: int,
    section: str,
    academic_year: str,
    exclude_id: int | None = None,
) -> None:
    stmt = select(AcademicClass.id).where(
        AcademicClass.major == major,
        AcademicClass.year == year,
        AcademicClass.section == section,
        AcademicClass.academic_year == academic_year,
    )
    if exclude_id is not None:
        stmt = stmt.where(AcademicClass.id != exclude_id)
    if db.execute(stmt).first() is not None:
        raise AppException(
            "A class with this major/year/section/academic year already exists",
            status_code=status.HTTP_409_CONFLICT,
            code="duplicate_class",
        )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def get_class(db: Session, class_id: int) -> AcademicClass:
    cls = db.get(AcademicClass, class_id)
    if cls is None:
        raise AppException(
            "Class not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="class_not_found",
        )
    return cls


def list_classes(
    db: Session,
    *,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[AcademicClass], int]:
    stmt = select(AcademicClass)
    count_stmt = select(func.count()).select_from(AcademicClass)

    if active_only:
        stmt = stmt.where(AcademicClass.is_active.is_(True))
        count_stmt = count_stmt.where(AcademicClass.is_active.is_(True))

    total = db.scalar(count_stmt) or 0
    items = (
        db.execute(
            stmt.order_by(
                AcademicClass.academic_year.desc(),
                AcademicClass.major,
                AcademicClass.year,
                AcademicClass.section,
            )
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(items), total


def create_class(db: Session, data: ClassCreate) -> AcademicClass:
    # Auto-generate class_code if not provided.
    code = data.class_code or generate_class_code(
        data.major, data.academic_year, data.year, data.section
    )

    _assert_code_available(db, code)
    _assert_natural_key_available(db, data.major, data.year, data.section, data.academic_year)

    cls = AcademicClass(
        class_code=code,
        major=data.major.upper(),
        year=data.year,
        section=data.section.upper(),
        academic_year=data.academic_year,
    )
    db.add(cls)
    db.commit()
    db.refresh(cls)
    logger.info("Created academic class id=%s code=%s", cls.id, cls.class_code)
    return cls


def update_class(db: Session, class_id: int, data: ClassUpdate) -> AcademicClass:
    cls = get_class(db, class_id)
    payload = data.model_dump(exclude_unset=True)

    # Track which fields would change for natural-key re-validation.
    new_major = payload.get("major", cls.major)
    new_year = payload.get("year", cls.year)
    new_section = payload.get("section", cls.section)
    new_academic_year = payload.get("academic_year", cls.academic_year)

    # If natural key fields changed, validate uniqueness.
    nk_changed = (
        new_major != cls.major
        or new_year != cls.year
        or new_section != cls.section
        or new_academic_year != cls.academic_year
    )
    if nk_changed:
        _assert_natural_key_available(
            db, new_major, new_year, new_section, new_academic_year,
            exclude_id=cls.id,
        )

    # Handle class_code: if provided explicitly use it; if natural key changed
    # and code wasn't provided, regenerate.
    if "class_code" in payload and payload["class_code"] is not None:
        new_code = payload["class_code"]
    elif nk_changed:
        new_code = generate_class_code(new_major, new_academic_year, new_year, new_section)
    else:
        new_code = None  # no change

    if new_code is not None and new_code != cls.class_code:
        _assert_code_available(db, new_code, exclude_id=cls.id)
        cls.class_code = new_code

    # Apply remaining fields.
    for field_name in ("major", "year", "section", "academic_year", "is_active"):
        if field_name in payload:
            value = payload[field_name]
            if field_name == "major":
                value = value.upper()
            elif field_name == "section":
                value = value.upper()
            setattr(cls, field_name, value)

    db.commit()
    db.refresh(cls)
    logger.info("Updated academic class id=%s code=%s", cls.id, cls.class_code)
    return cls


def delete_class(db: Session, class_id: int) -> None:
    """Delete a class if no students are currently assigned to it."""
    cls = get_class(db, class_id)

    student_count = db.scalar(
        select(func.count()).select_from(Student).where(Student.class_id == class_id)
    ) or 0
    if student_count > 0:
        raise AppException(
            f"Cannot delete class with {student_count} assigned student(s). "
            "Reassign or remove students first.",
            status_code=status.HTTP_409_CONFLICT,
            code="class_has_students",
        )

    db.delete(cls)
    db.commit()
    logger.info("Deleted academic class id=%s code=%s", class_id, cls.class_code)


def get_class_faculty(db: Session, class_id: int) -> list[dict]:
    """Return faculty assigned to a class."""
    get_class(db, class_id)  # validates class exists
    rows = db.execute(
        select(User.id, User.username)
        .join(FacultyClass, FacultyClass.user_id == User.id)
        .where(FacultyClass.class_id == class_id)
        .order_by(User.username)
    ).all()
    return [{"user_id": r[0], "username": r[1]} for r in rows]
