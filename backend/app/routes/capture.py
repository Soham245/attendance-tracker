"""Dataset capture runtime routes.

Thin layer: validate inputs, call the capture service, wrap the snapshot in
the standardized response envelope. Admin-gated for control endpoints;
status is faculty-readable to support polling from operator dashboards.
"""
from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import DBSession, require_admin, require_faculty_or_admin
from app.database.schemas.capture_schema import CaptureStartRequest, CaptureStatus
from app.database.schemas.response import APIResponse
from app.services import capture_service


router = APIRouter(prefix="/capture", tags=["Capture"])


@router.post(
    "/start",
    response_model=APIResponse[CaptureStatus],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_admin)],
)
def start_capture(
    payload: CaptureStartRequest,
    request: Request,
    db: DBSession,
) -> APIResponse[CaptureStatus]:
    snapshot = capture_service.start_capture(
        db,
        request.app.state,
        student_id=payload.student_id,
        replace=payload.replace,
    )
    # Enrich with dataset size for the response (matches /status shape).
    snapshot["dataset_image_count"] = capture_service.get_status_with_dataset_size(
        db, request.app.state
    )["dataset_image_count"]
    return APIResponse.ok(
        data=CaptureStatus(**snapshot), message="Capture session starting"
    )


@router.post(
    "/stop",
    response_model=APIResponse[CaptureStatus],
    dependencies=[Depends(require_admin)],
)
def stop_capture(request: Request, db: DBSession) -> APIResponse[CaptureStatus]:
    snapshot = capture_service.stop_capture(request.app.state)
    snapshot["dataset_image_count"] = capture_service.get_status_with_dataset_size(
        db, request.app.state
    )["dataset_image_count"]
    return APIResponse.ok(
        data=CaptureStatus(**snapshot), message="Capture session stopping"
    )


@router.get(
    "/status",
    response_model=APIResponse[CaptureStatus],
    dependencies=[Depends(require_faculty_or_admin)],
)
def get_status(request: Request, db: DBSession) -> APIResponse[CaptureStatus]:
    snapshot = capture_service.get_status_with_dataset_size(db, request.app.state)
    return APIResponse.ok(data=CaptureStatus(**snapshot))
