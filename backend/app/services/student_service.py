"""Student CRUD + dataset folder lifecycle.

Owns metadata writes and coordinates with the local storage layer so the
filesystem stays consistent with the DB. Recognition / training / inference
remain strictly out of scope.
"""
from typing import List, Tuple

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.database.models.academic_class import AcademicClass
from app.database.models.student import Student
from app.database.schemas.student_schema import StudentCreate, StudentUpdate
from app.recognition.identity_validator import invalidate as invalidate_identity
from app.recognition.model_manager import get_active_labels, has_active_model
from app.storage.local import (
    ensure_student_dataset,
    remove_student_dataset,
    student_dataset_relpath,
)


logger = get_logger("attendai.students")


def _assert_roll_available(db: Session, roll_number: str, exclude_id: int | None = None) -> None:
    stmt = select(Student.id).where(Student.roll_number == roll_number)
    if exclude_id is not None:
        stmt = stmt.where(Student.id != exclude_id)
    if db.execute(stmt).first() is not None:
        raise AppException(
            "Roll number already exists",
            status_code=status.HTTP_409_CONFLICT,
            code="duplicate_roll_number",
        )


def _assert_class_valid(db: Session, class_id: int | None) -> None:
    """Validate that the given class_id refers to an existing, active class."""
    if class_id is None:
        return
    cls = db.get(AcademicClass, class_id)
    if cls is None:
        raise AppException(
            "Class not found",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_class_id",
        )
    if not cls.is_active:
        raise AppException(
            "Cannot assign student to an inactive class",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="inactive_class",
        )


def _assert_email_available(db: Session, email: str | None, exclude_id: int | None = None) -> None:
    if not email:
        return
    stmt = select(Student.id).where(Student.email == email)
    if exclude_id is not None:
        stmt = stmt.where(Student.id != exclude_id)
    if db.execute(stmt).first() is not None:
        raise AppException(
            "Email already in use",
            status_code=status.HTTP_409_CONFLICT,
            code="duplicate_email",
        )


def get_student(db: Session, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise AppException(
            "Student not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="student_not_found",
        )
    return student


def list_students(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    class_id: int | None = None,
    status: str | None = None,
) -> Tuple[List[Student], int]:
    base = select(Student)
    count_base = select(func.count()).select_from(Student)
    if class_id is not None:
        # Active students have class_id set; graduated/inactive students have
        # class_id=NULL but last_class_id preserves their former class.  Match
        # both so the class scope shows all students that belong (or belonged)
        # to this class.
        class_filter = or_(
            Student.class_id == class_id,
            Student.last_class_id == class_id,
        )
        base = base.where(class_filter)
        count_base = count_base.where(class_filter)
    if status is not None:
        base = base.where(Student.status == status)
        count_base = count_base.where(Student.status == status)
    total = db.scalar(count_base) or 0
    items = (
        db.execute(base.order_by(Student.id).offset(skip).limit(limit))
        .scalars()
        .all()
    )
    return list(items), total


def create_student(db: Session, data: StudentCreate) -> Student:
    _assert_roll_available(db, data.roll_number)
    _assert_email_available(db, data.email)
    _assert_class_valid(db, data.class_id)

    student = Student(
        name=data.name,
        roll_number=data.roll_number,
        department=data.department,
        email=data.email,
        phone=data.phone,
        class_id=data.class_id,
    )
    db.add(student)
    db.flush()  # assigns student.id

    student.dataset_path = student_dataset_relpath(student.id)
    ensure_student_dataset(student.id)

    db.commit()
    db.refresh(student)
    logger.info("Created student id=%s roll=%s", student.id, student.roll_number)
    return student


def update_student(db: Session, student_id: int, data: StudentUpdate) -> Student:
    student = get_student(db, student_id)
    payload = data.model_dump(exclude_unset=True)

    if "roll_number" in payload and payload["roll_number"] != student.roll_number:
        _assert_roll_available(db, payload["roll_number"], exclude_id=student.id)
    if "email" in payload and payload["email"] != student.email:
        _assert_email_available(db, payload["email"], exclude_id=student.id)
    if "class_id" in payload and payload["class_id"] != student.class_id:
        _assert_class_valid(db, payload["class_id"])

    for field, value in payload.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)
    logger.info("Updated student id=%s fields=%s", student.id, sorted(payload.keys()))
    return student


def delete_student(db: Session, student_id: int) -> dict:
    """Delete student, cascade attendance (FK), clean up dataset, mark model stale.

    Returns a dict with `model_stale: True` when the deleted student was part
    of the active recognition model so the frontend can show a retraining prompt.
    """
    student = get_student(db, student_id)
    db.delete(student)
    db.commit()

    # Recognition runtime caches identity existence; drop the entry so any
    # immediately-following prediction for this id reaches the DB and is
    # correctly treated as a stale-model artifact.
    invalidate_identity(student_id)

    remove_student_dataset(student_id)

    # If the active model included this student, the model is now stale —
    # it would still "recognize" a face as this (deleted) student.
    model_stale = False
    if has_active_model():
        labels = get_active_labels() or {}
        if str(student_id) in labels:
            model_stale = True
            logger.info(
                "Active model includes deleted student_id=%s — model is stale",
                student_id,
            )

    logger.info("Deleted student id=%s model_stale=%s", student_id, model_stale)
    return {"model_stale": model_stale}
