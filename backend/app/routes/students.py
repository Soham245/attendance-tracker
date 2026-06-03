from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.config.constants import API_TAG_STUDENTS
from app.core.dependencies import DBSession, require_admin, require_faculty_or_admin
from app.database.schemas.response import APIResponse
from app.database.schemas.student_schema import (
    StudentCreate,
    StudentListResponse,
    StudentResponse,
    StudentUpdate,
)
from app.services import student_service


class BulkDeleteRequest(BaseModel):
    ids: List[int]


router = APIRouter(prefix="/students", tags=[API_TAG_STUDENTS])


@router.post(
    "",
    response_model=APIResponse[StudentResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_student(payload: StudentCreate, db: DBSession) -> APIResponse[StudentResponse]:
    student = student_service.create_student(db, payload)
    return APIResponse.ok(
        data=StudentResponse.from_orm_with_class(student), message="Student created"
    )


@router.get(
    "",
    response_model=APIResponse[StudentListResponse],
    dependencies=[Depends(require_faculty_or_admin)],
)
def list_students(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    class_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None, description="Filter by lifecycle status: active, graduated, inactive"),
) -> APIResponse[StudentListResponse]:
    items, total = student_service.list_students(
        db, skip=skip, limit=limit, class_id=class_id, status=status,
    )
    return APIResponse.ok(
        data=StudentListResponse(
            items=[StudentResponse.from_orm_with_class(s) for s in items],
            total=total,
        )
    )


@router.get(
    "/{student_id}",
    response_model=APIResponse[StudentResponse],
    dependencies=[Depends(require_faculty_or_admin)],
)
def get_student(student_id: int, db: DBSession) -> APIResponse[StudentResponse]:
    student = student_service.get_student(db, student_id)
    return APIResponse.ok(data=StudentResponse.from_orm_with_class(student))


@router.patch(
    "/{student_id}",
    response_model=APIResponse[StudentResponse],
    dependencies=[Depends(require_admin)],
)
def update_student(
    student_id: int, payload: StudentUpdate, db: DBSession
) -> APIResponse[StudentResponse]:
    student = student_service.update_student(db, student_id, payload)
    return APIResponse.ok(
        data=StudentResponse.from_orm_with_class(student), message="Student updated"
    )


@router.delete(
    "/{student_id}",
    response_model=APIResponse[dict],
    dependencies=[Depends(require_admin)],
)
def delete_student(student_id: int, db: DBSession) -> APIResponse[dict]:
    result = student_service.delete_student(db, student_id)
    return APIResponse.ok(
        data={"id": student_id, "model_stale": result.get("model_stale", False)},
        message="Student deleted",
    )


@router.post(
    "/bulk-delete",
    response_model=APIResponse[dict],
    dependencies=[Depends(require_admin)],
)
def bulk_delete_students(body: BulkDeleteRequest, db: DBSession) -> APIResponse[dict]:
    """Delete multiple students."""
    deleted = 0
    model_stale = False
    for sid in body.ids:
        try:
            result = student_service.delete_student(db, sid)
            if result.get("model_stale"):
                model_stale = True
            deleted += 1
        except Exception:
            continue
    return APIResponse.ok(
        data={"deleted": deleted, "model_stale": model_stale},
        message=f"Deleted {deleted} student(s)",
    )
