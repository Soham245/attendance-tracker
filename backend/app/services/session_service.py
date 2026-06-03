"""Attendance session lifecycle: create, end, list, detail.

Every attendance session belongs to exactly one academic class and one
faculty member.  The orchestration service calls into here when
starting/stopping the live recognition session.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.database.models.academic_class import AcademicClass
from app.database.models.attendance import Attendance
from app.database.models.attendance_session import AttendanceSession
from app.database.models.faculty_class import FacultyClass
from app.database.models.student import Student


logger = get_logger("attendai.sessions")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_class_exists(db: Session, class_id: int) -> AcademicClass:
    """Return the class or raise 404."""
    cls = db.get(AcademicClass, class_id)
    if cls is None:
        raise AppException(
            "Class not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="class_not_found",
        )
    if not cls.is_active:
        raise AppException(
            "Cannot start session for an inactive class",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="class_inactive",
        )
    return cls


def _assert_faculty_access(db: Session, faculty_id: int, class_id: int) -> None:
    """Verify the faculty member is assigned to this class."""
    row = db.execute(
        select(FacultyClass.id).where(
            FacultyClass.user_id == faculty_id,
            FacultyClass.class_id == class_id,
        )
    ).first()
    if row is None:
        raise AppException(
            "You are not assigned to this class",
            status_code=status.HTTP_403_FORBIDDEN,
            code="faculty_not_assigned",
        )


def _generate_session_name(cls: AcademicClass) -> str:
    """Auto-generate a human-readable session name."""
    now = datetime.now(timezone.utc)
    return f"{cls.class_code} — {now.strftime('%d %b %Y %H:%M')}"


def allowed_student_ids(db: Session, class_id: int) -> Set[int]:
    """Return the set of *active* student IDs enrolled in the given class.

    Used by the orchestration layer to scope recognition filtering at
    session start. Only students with ``status='active'`` are included —
    graduated or inactive students must not be recognized.
    """
    rows = db.execute(
        select(Student.id).where(
            Student.class_id == class_id,
            Student.status == "active",
        )
    ).scalars().all()
    return set(rows)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_session(
    db: Session,
    *,
    class_id: int,
    faculty_id: int,
    session_name: Optional[str] = None,
    is_admin: bool = False,
) -> AttendanceSession:
    """Create a new attendance session for a class.

    Admins bypass the faculty-class assignment check.
    """
    cls = _assert_class_exists(db, class_id)
    if not is_admin:
        _assert_faculty_access(db, faculty_id, class_id)

    name = session_name or _generate_session_name(cls)

    session = AttendanceSession(
        session_name=name,
        class_id=class_id,
        faculty_id=faculty_id,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(
        "Session created id=%s class_id=%s faculty_id=%s name='%s'",
        session.id, class_id, faculty_id, name,
    )
    return session


def end_session(db: Session, session_id: int) -> AttendanceSession:
    """Mark a session as ended."""
    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise AppException(
            "Session not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="session_not_found",
        )
    if session.status != "active":
        raise AppException(
            f"Session is already '{session.status}'",
            status_code=status.HTTP_409_CONFLICT,
            code="session_not_active",
        )
    session.ended_at = datetime.now(timezone.utc)
    session.status = "ended"
    db.commit()
    db.refresh(session)
    logger.info("Session ended id=%s", session_id)
    return session


def delete_session(db: Session, session_id: int) -> None:
    """Delete a session and all its attendance records."""
    session = get_session(db, session_id)
    # Remove linked attendance records first.
    from sqlalchemy import delete as sa_delete
    db.execute(sa_delete(Attendance).where(Attendance.session_id == session_id))
    db.delete(session)
    db.commit()
    logger.info("Session deleted id=%s", session_id)


def get_session(db: Session, session_id: int) -> AttendanceSession:
    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise AppException(
            "Session not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="session_not_found",
        )
    return session


def get_session_with_count(
    db: Session, session_id: int
) -> Tuple[AttendanceSession, int]:
    """Return a session and its attendance count."""
    session = get_session(db, session_id)
    count = db.scalar(
        select(func.count())
        .select_from(Attendance)
        .where(Attendance.session_id == session_id)
    ) or 0
    return session, count


def list_sessions(
    db: Session,
    *,
    faculty_id: Optional[int] = None,
    class_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[AttendanceSession], int, dict[int, int]]:
    """List sessions with optional filters.

    Returns ``(items, total, counts_map)`` where ``counts_map`` maps
    ``session_id → attendance_count`` for the returned page.

    ``date_from`` / ``date_to`` accept ISO-8601 date strings (YYYY-MM-DD).
    ``date_to`` is inclusive — the filter covers through end-of-day.
    """
    stmt = select(AttendanceSession)
    count_stmt = select(func.count()).select_from(AttendanceSession)

    if faculty_id is not None:
        stmt = stmt.where(AttendanceSession.faculty_id == faculty_id)
        count_stmt = count_stmt.where(AttendanceSession.faculty_id == faculty_id)
    if class_id is not None:
        stmt = stmt.where(AttendanceSession.class_id == class_id)
        count_stmt = count_stmt.where(AttendanceSession.class_id == class_id)
    if date_from is not None:
        stmt = stmt.where(AttendanceSession.started_at >= date_from)
        count_stmt = count_stmt.where(AttendanceSession.started_at >= date_from)
    if date_to is not None:
        # Include the entire end day.
        stmt = stmt.where(AttendanceSession.started_at < date_to + "T23:59:59.999999")
        count_stmt = count_stmt.where(AttendanceSession.started_at < date_to + "T23:59:59.999999")

    total = db.scalar(count_stmt) or 0
    items = list(
        db.execute(
            stmt.order_by(AttendanceSession.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    # Batch-fetch attendance counts for the page.
    session_ids = [s.id for s in items]
    counts_map: dict[int, int] = {}
    if session_ids:
        rows = db.execute(
            select(
                Attendance.session_id,
                func.count().label("cnt"),
            )
            .where(Attendance.session_id.in_(session_ids))
            .group_by(Attendance.session_id)
        ).all()
        counts_map = {r[0]: r[1] for r in rows}

    return items, total, counts_map
