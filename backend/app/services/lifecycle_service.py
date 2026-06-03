"""Student lifecycle operations: graduate, deactivate, restore.

Lifecycle changes are blocked while a recognition session is active to avoid
runtime corruption. Each operation marks the recognition model as stale and
records a reason so the dashboard can surface actionable warnings.

All operations preserve attendance history — only ``class_id`` and ``status``
change on the student row. No attendance or session records are touched.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import status as http_status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sqlalchemy import func

from app.config.constants import get_program_duration
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.database.models.student import Student
from app.database.models.academic_class import AcademicClass
from app.database.models.faculty_class import FacultyClass
from app.recognition.identity_validator import invalidate as invalidate_identity
from app.recognition.model_manager import get_active_labels, has_active_model


logger = get_logger("attendai.lifecycle")


# Valid student statuses
STATUS_ACTIVE = "active"
STATUS_GRADUATED = "graduated"
STATUS_INACTIVE = "inactive"
_VALID_STATUSES = {STATUS_ACTIVE, STATUS_GRADUATED, STATUS_INACTIVE}


# ---------------------------------------------------------------------------
# Session safety guard
# ---------------------------------------------------------------------------

def _require_no_active_session(app_state: Any) -> None:
    """Block lifecycle ops while a recognition session is running."""
    active = getattr(app_state, "active_session", None)
    if active:
        raise AppException(
            "Cannot modify student lifecycle while an attendance session is "
            "running. Stop the session first.",
            status_code=http_status.HTTP_409_CONFLICT,
            code="session_active",
        )


# ---------------------------------------------------------------------------
# Model stale tracking
# ---------------------------------------------------------------------------

def _mark_model_stale(app_state: Any, reason: str, count: int = 1) -> None:
    """Set the model_stale flag and append a human-readable reason.

    Reasons accumulate on ``app.state.model_stale_reasons`` (a list of dicts)
    so the dashboard can display why retraining is needed.
    """
    runtime = getattr(app_state, "recognition_runtime", None)
    if isinstance(runtime, dict):
        if not runtime.get("model_stale"):
            runtime["model_stale"] = True
            runtime["model_stale_since"] = datetime.now(timezone.utc).isoformat()

    # Accumulate reasons (initialise list if needed).
    reasons: List[Dict[str, Any]] = getattr(app_state, "model_stale_reasons", None)
    if reasons is None:
        reasons = []
        app_state.model_stale_reasons = reasons
    reasons.append({
        "reason": reason,
        "count": count,
        "at": datetime.now(timezone.utc).isoformat(),
    })


def _check_model_includes(student_id: int) -> bool:
    """Return True if the active model gallery contains this student."""
    if not has_active_model():
        return False
    labels = get_active_labels() or {}
    return str(student_id) in labels


# ---------------------------------------------------------------------------
# Lifecycle operations
# ---------------------------------------------------------------------------

def graduate_student(
    db: Session,
    app_state: Any,
    student_id: int,
) -> Dict[str, Any]:
    """Graduate a single student.

    - Sets status to 'graduated'
    - Moves class_id to last_class_id
    - Sets graduated_at
    - Marks model stale if student is in active gallery
    - Invalidates identity validator cache
    """
    _require_no_active_session(app_state)

    student = _get_student_or_404(db, student_id)

    if student.status == STATUS_GRADUATED:
        raise AppException(
            "Student is already graduated",
            status_code=http_status.HTTP_409_CONFLICT,
            code="already_graduated",
        )
    if student.status != STATUS_ACTIVE:
        raise AppException(
            f"Cannot graduate a student with status '{student.status}'. "
            "Restore to active first.",
            status_code=http_status.HTTP_400_BAD_REQUEST,
            code="invalid_status_transition",
        )

    batch_id = uuid.uuid4().hex

    old_class_id = student.class_id
    student.last_class_id = student.class_id
    student.class_id = None
    student.status = STATUS_GRADUATED
    student.graduated_at = datetime.now(timezone.utc)
    student.lifecycle_batch_id = batch_id

    db.commit()
    db.refresh(student)

    # Invalidate identity cache so the runtime sees the change immediately.
    invalidate_identity(student_id)

    if _check_model_includes(student_id):
        _mark_model_stale(app_state, "student_graduated", 1)

    logger.info(
        "Student graduated id=%s old_class_id=%s batch=%s",
        student_id, old_class_id, batch_id,
    )
    return {
        "student_id": student_id,
        "old_status": STATUS_ACTIVE,
        "new_status": STATUS_GRADUATED,
        "batch_id": batch_id,
        "model_stale": _check_model_includes(student_id),
    }


def deactivate_student(
    db: Session,
    app_state: Any,
    student_id: int,
) -> Dict[str, Any]:
    """Deactivate a student (transfer, dropout, suspension).

    Same mechanics as graduation but with status 'inactive' and no
    graduated_at timestamp.
    """
    _require_no_active_session(app_state)

    student = _get_student_or_404(db, student_id)

    if student.status == STATUS_INACTIVE:
        raise AppException(
            "Student is already inactive",
            status_code=http_status.HTTP_409_CONFLICT,
            code="already_inactive",
        )
    if student.status != STATUS_ACTIVE:
        raise AppException(
            f"Cannot deactivate a student with status '{student.status}'. "
            "Restore to active first.",
            status_code=http_status.HTTP_400_BAD_REQUEST,
            code="invalid_status_transition",
        )

    batch_id = uuid.uuid4().hex

    old_class_id = student.class_id
    student.last_class_id = student.class_id
    student.class_id = None
    student.status = STATUS_INACTIVE
    student.lifecycle_batch_id = batch_id

    db.commit()
    db.refresh(student)

    invalidate_identity(student_id)

    if _check_model_includes(student_id):
        _mark_model_stale(app_state, "student_deactivated", 1)

    logger.info(
        "Student deactivated id=%s old_class_id=%s batch=%s",
        student_id, old_class_id, batch_id,
    )
    return {
        "student_id": student_id,
        "old_status": STATUS_ACTIVE,
        "new_status": STATUS_INACTIVE,
        "batch_id": batch_id,
        "model_stale": _check_model_includes(student_id),
    }


def restore_student(
    db: Session,
    app_state: Any,
    student_id: int,
    target_class_id: int,
) -> Dict[str, Any]:
    """Restore a graduated or inactive student to active status.

    The admin must specify a target class. The student becomes immediately
    active in that class, but will NOT be recognized until the model is
    retrained (training_required is set, model marked stale).
    """
    _require_no_active_session(app_state)

    student = _get_student_or_404(db, student_id)

    if student.status == STATUS_ACTIVE:
        raise AppException(
            "Student is already active",
            status_code=http_status.HTTP_409_CONFLICT,
            code="already_active",
        )

    # Validate target class.
    target_class = db.get(AcademicClass, target_class_id)
    if target_class is None:
        raise AppException(
            "Target class not found",
            status_code=http_status.HTTP_404_NOT_FOUND,
            code="class_not_found",
        )
    if not target_class.is_active:
        raise AppException(
            "Cannot restore student to an inactive class",
            status_code=http_status.HTTP_400_BAD_REQUEST,
            code="inactive_class",
        )

    old_status = student.status
    student.class_id = target_class_id
    student.status = STATUS_ACTIVE
    student.graduated_at = None
    student.last_class_id = None
    student.lifecycle_batch_id = None
    student.training_required = True

    db.commit()
    db.refresh(student)

    # No identity cache invalidation needed — restoring makes them valid.
    # But the model needs retraining to include them.
    _mark_model_stale(app_state, "student_restored", 1)

    logger.info(
        "Student restored id=%s old_status=%s target_class_id=%s",
        student_id, old_status, target_class_id,
    )
    return {
        "student_id": student_id,
        "old_status": old_status,
        "new_status": STATUS_ACTIVE,
        "target_class_id": target_class_id,
        "model_stale": True,
    }


# ---------------------------------------------------------------------------
# Class-level operations
# ---------------------------------------------------------------------------

def promote_class(
    db: Session,
    app_state: Any,
    source_class_id: int,
    target_class_id: int,
) -> Dict[str, Any]:
    """Promote all active students from one class to another.

    Only ``class_id`` changes — status, datasets, embeddings, and attendance
    history are untouched. No retraining needed (same students, same faces).
    """
    _require_no_active_session(app_state)

    source = _get_class_or_404(db, source_class_id)
    target = _get_class_or_404(db, target_class_id)

    if source_class_id == target_class_id:
        raise AppException(
            "Source and target class must be different",
            status_code=http_status.HTTP_400_BAD_REQUEST,
            code="same_class",
        )
    if not target.is_active:
        raise AppException(
            "Cannot promote to an inactive class",
            status_code=http_status.HTTP_400_BAD_REQUEST,
            code="inactive_class",
        )

    students = db.execute(
        select(Student).where(
            Student.class_id == source_class_id,
            Student.status == STATUS_ACTIVE,
        )
    ).scalars().all()

    if not students:
        raise AppException(
            "No active students in the source class to promote",
            status_code=http_status.HTTP_400_BAD_REQUEST,
            code="no_students",
        )

    # Check how many are already in the target (double-promote safety).
    already_in_target = 0
    promoted = 0
    for s in students:
        if s.class_id == target_class_id:
            already_in_target += 1
            continue
        s.class_id = target_class_id
        promoted += 1

    db.commit()

    # Check if target class has faculty assigned.
    faculty_count = db.scalar(
        select(func.count()).select_from(FacultyClass).where(
            FacultyClass.class_id == target_class_id,
        )
    ) or 0

    warnings = []
    if faculty_count == 0:
        warnings.append("Target class has no faculty assigned.")

    logger.info(
        "Class promoted source=%s target=%s promoted=%d skipped=%d",
        source.class_code, target.class_code, promoted, already_in_target,
    )
    return {
        "promoted_count": promoted,
        "already_in_target": already_in_target,
        "source_class": source.class_code,
        "target_class": target.class_code,
        "warnings": warnings,
    }


def graduate_class(
    db: Session,
    app_state: Any,
    class_id: int,
) -> Dict[str, Any]:
    """Graduate all active students in a class.

    Each student gets:
    - status = 'graduated'
    - last_class_id = class_id (preserves last class reference)
    - class_id = NULL (removed from active roster)
    - graduated_at = now
    - lifecycle_batch_id = shared batch UUID (enables batch undo)

    The recognition model is marked stale. Identity validator cache is
    invalidated for every graduated student.
    """
    _require_no_active_session(app_state)

    cls = _get_class_or_404(db, class_id)

    students = db.execute(
        select(Student).where(
            Student.class_id == class_id,
            Student.status == STATUS_ACTIVE,
        )
    ).scalars().all()

    if not students:
        raise AppException(
            "No active students in this class to graduate",
            status_code=http_status.HTTP_400_BAD_REQUEST,
            code="no_students",
        )

    batch_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    model_affected = 0

    for s in students:
        s.last_class_id = s.class_id
        s.class_id = None
        s.status = STATUS_GRADUATED
        s.graduated_at = now
        s.lifecycle_batch_id = batch_id

    db.commit()

    # Invalidate identity cache for all graduated students and check model.
    for s in students:
        invalidate_identity(s.id)
        if _check_model_includes(s.id):
            model_affected += 1

    if model_affected > 0:
        _mark_model_stale(app_state, "student_graduated", model_affected)

    # Count already-graduated students for informational purposes.
    already_graduated = db.scalar(
        select(func.count()).select_from(Student).where(
            Student.last_class_id == class_id,
            Student.status == STATUS_GRADUATED,
            Student.lifecycle_batch_id != batch_id,
        )
    ) or 0

    logger.info(
        "Class graduated class=%s batch=%s graduated=%d model_affected=%d",
        cls.class_code, batch_id, len(students), model_affected,
    )
    return {
        "graduated_count": len(students),
        "already_graduated_count": already_graduated,
        "batch_id": batch_id,
        "class_code": cls.class_code,
        "model_stale": model_affected > 0,
    }


def restore_batch(
    db: Session,
    app_state: Any,
    batch_id: str,
    target_class_id: int,
) -> Dict[str, Any]:
    """Restore all students from a lifecycle batch to active status.

    Used to undo a class-wide graduation or deactivation. The admin must
    specify a target class (the original class may have been deactivated
    or may no longer be appropriate).
    """
    _require_no_active_session(app_state)

    # Validate target class.
    target_class = _get_class_or_404(db, target_class_id)
    if not target_class.is_active:
        raise AppException(
            "Cannot restore students to an inactive class",
            status_code=http_status.HTTP_400_BAD_REQUEST,
            code="inactive_class",
        )

    students = db.execute(
        select(Student).where(
            Student.lifecycle_batch_id == batch_id,
            Student.status.in_([STATUS_GRADUATED, STATUS_INACTIVE]),
        )
    ).scalars().all()

    if not students:
        raise AppException(
            "No students found for this batch, or all are already active",
            status_code=http_status.HTTP_404_NOT_FOUND,
            code="batch_not_found",
        )

    for s in students:
        s.class_id = target_class_id
        s.status = STATUS_ACTIVE
        s.graduated_at = None
        s.last_class_id = None
        s.lifecycle_batch_id = None
        s.training_required = True

    db.commit()

    _mark_model_stale(app_state, "student_restored", len(students))

    logger.info(
        "Batch restored batch=%s target_class=%s count=%d",
        batch_id, target_class.class_code, len(students),
    )
    return {
        "restored_count": len(students),
        "batch_id": batch_id,
        "target_class": target_class.class_code,
        "model_stale": True,
    }


# ---------------------------------------------------------------------------
# Academic year helpers
# ---------------------------------------------------------------------------

def next_academic_year(current: str) -> str:
    """Advance an academic year string by one.

    ``"2026-27"`` → ``"2027-28"``
    ``"2026-2027"`` → ``"2027-2028"``
    """
    parts = current.split("-")
    start = int(parts[0])
    end_part = parts[1] if len(parts) > 1 else str(start + 1)
    new_start = start + 1
    if len(end_part) <= 2:
        new_end = str((new_start + 1) % 100).zfill(2)
    else:
        new_end = str(new_start + 1)
    return f"{new_start}-{new_end}"


# ---------------------------------------------------------------------------
# Auto-target resolution
# ---------------------------------------------------------------------------

def _resolve_target_class(
    db: Session,
    source: AcademicClass,
) -> AcademicClass | None:
    """Find the target class for promotion: same major, same section, year+1.

    Tries two strategies for academic_year matching:
    1. Same academic_year (cohort span style: all years share e.g. "2026-30")
    2. Next academic_year (single-year style: "2026-27" → "2027-28")

    This handles both conventions transparently.
    """
    target_year = source.year + 1

    # Strategy 1: same academic_year (cohort span — e.g. "2026-30" for all years).
    target = db.execute(
        select(AcademicClass).where(
            AcademicClass.major == source.major,
            AcademicClass.section == source.section,
            AcademicClass.year == target_year,
            AcademicClass.academic_year == source.academic_year,
            AcademicClass.is_active == True,  # noqa: E712
        )
    ).scalar_one_or_none()

    if target is not None:
        return target

    # Strategy 2: next academic_year (single-year style — "2026-27" → "2027-28").
    target_ay = next_academic_year(source.academic_year)
    return db.execute(
        select(AcademicClass).where(
            AcademicClass.major == source.major,
            AcademicClass.section == source.section,
            AcademicClass.year == target_year,
            AcademicClass.academic_year == target_ay,
            AcademicClass.is_active == True,  # noqa: E712
        )
    ).scalar_one_or_none()


def _count_active_students(db: Session, class_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(Student).where(
            Student.class_id == class_id,
            Student.status == STATUS_ACTIVE,
        )
    ) or 0


def _has_faculty(db: Session, class_id: int) -> bool:
    return (db.scalar(
        select(func.count()).select_from(FacultyClass).where(
            FacultyClass.class_id == class_id,
        )
    ) or 0) > 0


# ---------------------------------------------------------------------------
# Promotion preview
# ---------------------------------------------------------------------------

def preview_promotion(
    db: Session,
    *,
    class_id: int | None = None,
    major: str | None = None,
) -> Dict[str, Any]:
    """Build a promotion plan without executing anything.

    Pass ``class_id`` for a single class, or ``major`` for all active classes
    in that program.
    """
    if class_id is not None:
        source = _get_class_or_404(db, class_id)
        sources = [source]
        effective_major = source.major
    elif major is not None:
        sources = list(db.execute(
            select(AcademicClass).where(
                AcademicClass.major == major,
                AcademicClass.is_active == True,  # noqa: E712
            ).order_by(AcademicClass.year, AcademicClass.section)
        ).scalars().all())
        effective_major = major
    else:
        raise AppException(
            "Provide class_id or major",
            status_code=400,
            code="missing_parameter",
        )

    duration = get_program_duration(effective_major)
    items = []

    for src in sources:
        student_count = _count_active_students(db, src.id)
        is_final = src.year >= duration

        if student_count == 0:
            items.append({
                "source_class_id": src.id,
                "source_class_code": src.class_code,
                "source_year": src.year,
                "student_count": 0,
                "action": "skip",
                "target_class_id": None,
                "target_class_code": None,
                "target_missing": False,
                "target_has_faculty": False,
                "warnings": [],
            })
            continue

        if is_final:
            items.append({
                "source_class_id": src.id,
                "source_class_code": src.class_code,
                "source_year": src.year,
                "student_count": student_count,
                "action": "graduate",
                "target_class_id": None,
                "target_class_code": None,
                "target_missing": False,
                "target_has_faculty": False,
                "warnings": [],
            })
            continue

        # Not final year → resolve target.
        target = _resolve_target_class(db, src)
        warnings: List[str] = []
        if target and not _has_faculty(db, target.id):
            warnings.append(f"{target.class_code} has no faculty assigned.")

        items.append({
            "source_class_id": src.id,
            "source_class_code": src.class_code,
            "source_year": src.year,
            "student_count": student_count,
            "action": "promote",
            "target_class_id": target.id if target else None,
            "target_class_code": target.class_code if target else None,
            "target_missing": target is None,
            "target_has_faculty": _has_faculty(db, target.id) if target else False,
            "warnings": warnings,
        })

    return {
        "items": items,
        "program_duration": duration,
        "major": effective_major,
    }


# ---------------------------------------------------------------------------
# Batch execute (promote + graduate)
# ---------------------------------------------------------------------------

def execute_promotion(
    db: Session,
    app_state: Any,
    class_ids: List[int],
) -> Dict[str, Any]:
    """Execute promotions and graduations for the given class IDs.

    Re-resolves targets at execution time. Final-year classes are graduated;
    others are promoted to the auto-resolved target.
    """
    _require_no_active_session(app_state)

    promoted_results: List[Dict[str, Any]] = []
    graduated_results: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    warnings: List[str] = []
    model_stale = False

    for cid in class_ids:
        cls = db.get(AcademicClass, cid)
        if cls is None:
            skipped.append({"class_id": cid, "reason": "Class not found"})
            continue

        student_count = _count_active_students(db, cls.id)
        if student_count == 0:
            skipped.append({
                "class_id": cid,
                "class_code": cls.class_code,
                "reason": "No active students",
            })
            continue

        duration = get_program_duration(cls.major)
        is_final = cls.year >= duration

        if is_final:
            # Graduate.
            result = graduate_class(db, app_state, cls.id)
            graduated_results.append({
                "source": cls.class_code,
                "count": result["graduated_count"],
                "batch_id": result["batch_id"],
            })
            if result.get("model_stale"):
                model_stale = True
        else:
            # Promote — auto-resolve target.
            target = _resolve_target_class(db, cls)
            if target is None:
                skipped.append({
                    "class_id": cid,
                    "class_code": cls.class_code,
                    "reason": f"Target class not found ({cls.major} Y{cls.year + 1} {cls.section})",
                })
                continue
            result = promote_class(db, app_state, cls.id, target.id)
            promoted_results.append({
                "source": cls.class_code,
                "target": target.class_code,
                "count": result["promoted_count"],
            })
            if result.get("warnings"):
                warnings.extend(result["warnings"])

    return {
        "promoted": promoted_results,
        "graduated": graduated_results,
        "skipped": skipped,
        "warnings": warnings,
        "model_stale": model_stale,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_student_or_404(db: Session, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise AppException(
            "Student not found",
            status_code=http_status.HTTP_404_NOT_FOUND,
            code="student_not_found",
        )
    return student


def _get_class_or_404(db: Session, class_id: int) -> AcademicClass:
    cls = db.get(AcademicClass, class_id)
    if cls is None:
        raise AppException(
            "Class not found",
            status_code=http_status.HTTP_404_NOT_FOUND,
            code="class_not_found",
        )
    return cls
