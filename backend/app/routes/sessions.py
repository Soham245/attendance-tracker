"""Session history routes.

Admin sees all sessions; faculty sees only their own.
Includes session detail, session attendance listing, CSV export,
and single/bulk delete.
"""
from __future__ import annotations

import csv
import io
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.dependencies import DBSession, require_faculty_or_admin
from app.core.exceptions import AppException
from app.database.models.user import User
from app.database.schemas.attendance_schema import AttendanceListResponse, AttendanceResponse
from app.database.schemas.response import APIResponse
from app.database.schemas.session_schema import (
    SessionListResponse,
    SessionResponse,
)
from app.services import attendance_service, session_service


router = APIRouter(prefix="/sessions", tags=["Sessions"])

FacultyOrAdmin = Annotated[User, Depends(require_faculty_or_admin)]


class BulkDeleteRequest(BaseModel):
    ids: List[int]


def _assert_session_visible(session, user: User) -> None:
    """Faculty can only see their own sessions; admin sees all."""
    if user.role != "admin" and session.faculty_id != user.id:
        raise AppException(
            "Session not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="session_not_found",
        )


@router.get(
    "",
    response_model=APIResponse[SessionListResponse],
)
def list_sessions(
    db: DBSession,
    user: FacultyOrAdmin,
    class_id: Optional[int] = Query(None),
    faculty_id: Optional[int] = Query(None, description="Filter by faculty (admin only)"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date inclusive (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> APIResponse[SessionListResponse]:
    # Faculty only sees their own sessions; admin sees all.
    # Admin can optionally filter to a specific faculty member.
    if user.role == "admin":
        effective_faculty = faculty_id  # None = all, or specific faculty
    else:
        effective_faculty = user.id  # faculty always scoped to self

    items, total, counts_map = session_service.list_sessions(
        db,
        faculty_id=effective_faculty,
        class_id=class_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )

    responses = [
        SessionResponse.from_orm_with_relations(s, attendance_count=counts_map.get(s.id, 0))
        for s in items
    ]
    return APIResponse.ok(
        data=SessionListResponse(items=responses, total=total)
    )


@router.get(
    "/{session_id}",
    response_model=APIResponse[SessionResponse],
)
def get_session(
    session_id: int,
    db: DBSession,
    user: FacultyOrAdmin,
) -> APIResponse[SessionResponse]:
    session, count = session_service.get_session_with_count(db, session_id)
    _assert_session_visible(session, user)

    return APIResponse.ok(
        data=SessionResponse.from_orm_with_relations(session, attendance_count=count)
    )


@router.get(
    "/{session_id}/attendance",
    response_model=APIResponse[AttendanceListResponse],
)
def session_attendance(
    session_id: int,
    db: DBSession,
    user: FacultyOrAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> APIResponse[AttendanceListResponse]:
    """List attendance records for a specific session."""
    session = session_service.get_session(db, session_id)
    _assert_session_visible(session, user)

    items, total = attendance_service.list_attendance(
        db, session_id=session_id, skip=skip, limit=limit
    )
    return APIResponse.ok(
        data=AttendanceListResponse(
            items=[AttendanceResponse.model_validate(r) for r in items],
            total=total,
        )
    )


@router.get(
    "/{session_id}/export/csv",
)
def export_session_csv(
    session_id: int,
    db: DBSession,
    user: FacultyOrAdmin,
) -> StreamingResponse:
    """Export session attendance as CSV download."""
    session, _ = session_service.get_session_with_count(db, session_id)
    _assert_session_visible(session, user)

    # Fetch ALL attendance for this session (no pagination).
    items, _ = attendance_service.list_attendance(
        db, session_id=session_id, skip=0, limit=10000
    )

    class_code = ""
    if session.academic_class is not None:
        class_code = session.academic_class.class_code

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Student Name",
        "Roll Number",
        "Class",
        "Date",
        "Time",
        "Status",
        "Confidence",
    ])

    for record in items:
        student = record.student
        rec_at = record.recognized_at
        writer.writerow([
            student.name if student else "Unknown",
            student.roll_number if student else "",
            class_code,
            rec_at.strftime("%Y-%m-%d") if rec_at else "",
            rec_at.strftime("%H:%M:%S") if rec_at else "",
            record.status,
            f"{record.confidence:.2f}" if record.confidence is not None else "",
        ])

    buf.seek(0)
    safe_name = session.session_name.replace(" ", "_").replace("/", "-")[:50]
    filename = f"attendance_{safe_name}_{session_id}.csv"

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete(
    "/{session_id}",
    response_model=APIResponse[dict],
)
def delete_session(
    session_id: int,
    db: DBSession,
    user: FacultyOrAdmin,
) -> APIResponse[dict]:
    """Delete a session and its attendance records."""
    session = session_service.get_session(db, session_id)
    _assert_session_visible(session, user)
    session_service.delete_session(db, session_id)
    return APIResponse.ok(data={"id": session_id}, message="Session deleted")


@router.post(
    "/bulk-delete",
    response_model=APIResponse[dict],
)
def bulk_delete_sessions(
    body: BulkDeleteRequest,
    db: DBSession,
    user: FacultyOrAdmin,
) -> APIResponse[dict]:
    """Delete multiple sessions (and their attendance records)."""
    deleted = 0
    for sid in body.ids:
        try:
            session = session_service.get_session(db, sid)
            _assert_session_visible(session, user)
            session_service.delete_session(db, sid)
            deleted += 1
        except AppException:
            continue
    return APIResponse.ok(
        data={"deleted": deleted},
        message=f"Deleted {deleted} session(s)",
    )
