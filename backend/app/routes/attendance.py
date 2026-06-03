from datetime import date as date_t
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.config.constants import API_TAG_ATTENDANCE
from app.core.dependencies import DBSession, require_admin, require_faculty_or_admin
from app.database.schemas.attendance_schema import (
    AttendanceListResponse,
    AttendanceResponse,
)
from app.database.schemas.response import APIResponse
from app.services import attendance_service


class BulkDeleteRequest(BaseModel):
    ids: List[int]


router = APIRouter(
    prefix="/attendance",
    tags=[API_TAG_ATTENDANCE],
    dependencies=[Depends(require_faculty_or_admin)],
)


@router.get("", response_model=APIResponse[AttendanceListResponse])
def list_attendance(
    db: DBSession,
    student_id: Optional[int] = Query(default=None),
    class_id: Optional[int] = Query(default=None),
    on_date: Optional[date_t] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> APIResponse[AttendanceListResponse]:
    items, total = attendance_service.list_attendance(
        db, student_id=student_id, class_id=class_id, on_date=on_date, skip=skip, limit=limit
    )
    return APIResponse.ok(
        data=AttendanceListResponse(
            items=[AttendanceResponse.model_validate(r) for r in items],
            total=total,
        )
    )


@router.get("/{attendance_id}", response_model=APIResponse[AttendanceResponse])
def get_attendance(attendance_id: int, db: DBSession) -> APIResponse[AttendanceResponse]:
    record = attendance_service.get_attendance(db, attendance_id)
    return APIResponse.ok(data=AttendanceResponse.model_validate(record))


@router.delete(
    "/{attendance_id}",
    response_model=APIResponse[dict],
    dependencies=[Depends(require_faculty_or_admin)],
)
def delete_attendance(
    attendance_id: int, db: DBSession, request: Request
) -> APIResponse[dict]:
    info = attendance_service.delete_attendance(db, attendance_id)
    # Keep the operator's recent-recognitions feed consistent with persisted
    # truth: drop the matching event the runtime is still surfacing.
    attendance_service.invalidate_recent_event(
        request.app.state, info["student_id"], info["recognized_at"]
    )
    return APIResponse.ok(data={"id": attendance_id}, message="Attendance deleted")


@router.post(
    "/bulk-delete",
    response_model=APIResponse[dict],
    dependencies=[Depends(require_faculty_or_admin)],
)
def bulk_delete_attendance(
    body: BulkDeleteRequest, db: DBSession, request: Request
) -> APIResponse[dict]:
    """Delete multiple attendance records."""
    deleted = 0
    for aid in body.ids:
        try:
            info = attendance_service.delete_attendance(db, aid)
            attendance_service.invalidate_recent_event(
                request.app.state, info["student_id"], info["recognized_at"]
            )
            deleted += 1
        except Exception:
            continue
    return APIResponse.ok(
        data={"deleted": deleted},
        message=f"Deleted {deleted} record(s)",
    )


@router.get(
    "/students/{student_id}",
    response_model=APIResponse[AttendanceListResponse],
)
def student_attendance(
    student_id: int,
    db: DBSession,
    on_date: Optional[date_t] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> APIResponse[AttendanceListResponse]:
    items, total = attendance_service.list_attendance(
        db, student_id=student_id, on_date=on_date, skip=skip, limit=limit
    )
    return APIResponse.ok(
        data=AttendanceListResponse(
            items=[AttendanceResponse.model_validate(r) for r in items],
            total=total,
        )
    )
