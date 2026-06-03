"""Student and class lifecycle endpoints.

Admin-only. All operations are blocked while a recognition session is active
(409 Conflict). Each operation returns results including whether the
recognition model is now stale.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.config.constants import (
    API_TAG_STUDENTS,
    DEFAULT_PROGRAM_DURATION,
    PROGRAM_DURATIONS,
)
from app.core.dependencies import DBSession, require_admin
from app.database.schemas.response import APIResponse
from app.services import lifecycle_service


router = APIRouter(
    prefix="/lifecycle",
    tags=[API_TAG_STUDENTS],
    dependencies=[Depends(require_admin)],
)


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class RestoreRequest(BaseModel):
    target_class_id: int = Field(description="Class to enroll the student in")


class PromoteRequest(BaseModel):
    target_class_id: Optional[int] = Field(
        default=None,
        description="Target class. If omitted, auto-resolved from source class.",
    )


class BatchPromoteRequest(BaseModel):
    class_ids: List[int] = Field(description="Classes to promote/graduate")


class BatchRestoreRequest(BaseModel):
    target_class_id: int = Field(description="Class to enroll the restored students in")


# ---------------------------------------------------------------------------
# Program info
# ---------------------------------------------------------------------------

@router.get(
    "/programs",
    response_model=APIResponse[dict],
)
def get_programs() -> APIResponse[dict]:
    return APIResponse.ok(data={
        "programs": PROGRAM_DURATIONS,
        "default_duration": DEFAULT_PROGRAM_DURATION,
    })


# ---------------------------------------------------------------------------
# Promotion preview & execute
# ---------------------------------------------------------------------------

@router.get(
    "/promotion/preview",
    response_model=APIResponse[dict],
)
def promotion_preview(
    db: DBSession,
    class_id: Optional[int] = Query(None),
    major: Optional[str] = Query(None),
) -> APIResponse[dict]:
    result = lifecycle_service.preview_promotion(
        db, class_id=class_id, major=major,
    )
    return APIResponse.ok(data=result)


@router.post(
    "/promotion/execute",
    response_model=APIResponse[dict],
)
def promotion_execute(
    body: BatchPromoteRequest,
    db: DBSession,
    request: Request,
) -> APIResponse[dict]:
    result = lifecycle_service.execute_promotion(
        db, request.app.state, body.class_ids,
    )
    return APIResponse.ok(data=result, message="Promotion executed")


# ---------------------------------------------------------------------------
# Single-student endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/students/{student_id}/graduate",
    response_model=APIResponse[dict],
)
def graduate_student(
    student_id: int,
    db: DBSession,
    request: Request,
) -> APIResponse[dict]:
    result = lifecycle_service.graduate_student(
        db, request.app.state, student_id,
    )
    return APIResponse.ok(data=result, message="Student graduated")


@router.post(
    "/students/{student_id}/deactivate",
    response_model=APIResponse[dict],
)
def deactivate_student(
    student_id: int,
    db: DBSession,
    request: Request,
) -> APIResponse[dict]:
    result = lifecycle_service.deactivate_student(
        db, request.app.state, student_id,
    )
    return APIResponse.ok(data=result, message="Student deactivated")


@router.post(
    "/students/{student_id}/restore",
    response_model=APIResponse[dict],
)
def restore_student(
    student_id: int,
    body: RestoreRequest,
    db: DBSession,
    request: Request,
) -> APIResponse[dict]:
    result = lifecycle_service.restore_student(
        db, request.app.state, student_id, body.target_class_id,
    )
    return APIResponse.ok(data=result, message="Student restored")


# ---------------------------------------------------------------------------
# Class-level endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/classes/{class_id}/promote",
    response_model=APIResponse[dict],
)
def promote_class(
    class_id: int,
    body: PromoteRequest,
    db: DBSession,
    request: Request,
) -> APIResponse[dict]:
    if body.target_class_id is not None:
        target_id = body.target_class_id
    else:
        # Auto-resolve target.
        source = db.get(lifecycle_service.AcademicClass, class_id)
        if source is None:
            from app.core.exceptions import AppException
            raise AppException("Class not found", status_code=404, code="class_not_found")
        target = lifecycle_service._resolve_target_class(db, source)
        if target is None:
            from app.core.exceptions import AppException
            raise AppException(
                f"Target class not found. Expected: {source.major} Y{source.year + 1} "
                f"{source.section}. Create it first.",
                status_code=400,
                code="target_not_found",
            )
        target_id = target.id

    result = lifecycle_service.promote_class(
        db, request.app.state, class_id, target_id,
    )
    return APIResponse.ok(data=result, message="Class promoted")


@router.post(
    "/classes/{class_id}/graduate",
    response_model=APIResponse[dict],
)
def graduate_class(
    class_id: int,
    db: DBSession,
    request: Request,
) -> APIResponse[dict]:
    result = lifecycle_service.graduate_class(
        db, request.app.state, class_id,
    )
    return APIResponse.ok(data=result, message="Class graduated")


# ---------------------------------------------------------------------------
# Batch endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/batches/{batch_id}/restore",
    response_model=APIResponse[dict],
)
def restore_batch(
    batch_id: str,
    body: BatchRestoreRequest,
    db: DBSession,
    request: Request,
) -> APIResponse[dict]:
    result = lifecycle_service.restore_batch(
        db, request.app.state, batch_id, body.target_class_id,
    )
    return APIResponse.ok(data=result, message="Batch restored")
