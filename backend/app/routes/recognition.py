from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import require_admin, require_faculty_or_admin
from app.core.exceptions import AppException
from app.database.schemas.recognition_schema import RecognitionStatus
from app.database.schemas.response import APIResponse
from app.services import recognition_service


router = APIRouter(prefix="/recognition", tags=["Recognition"])


@router.post(
    "/start",
    response_model=APIResponse[RecognitionStatus],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_admin)],
)
def start_runtime(request: Request) -> APIResponse[RecognitionStatus]:
    try:
        snapshot = recognition_service.start(request.app.state)
    except RuntimeError as exc:
        raise AppException(
            str(exc),
            status_code=status.HTTP_409_CONFLICT,
            code="recognition_already_running",
        ) from exc
    return APIResponse.ok(
        data=RecognitionStatus(**snapshot), message="Recognition runtime starting"
    )


@router.post(
    "/stop",
    response_model=APIResponse[RecognitionStatus],
    dependencies=[Depends(require_admin)],
)
def stop_runtime(request: Request) -> APIResponse[RecognitionStatus]:
    try:
        snapshot = recognition_service.stop(request.app.state)
    except RuntimeError as exc:
        raise AppException(
            str(exc),
            status_code=status.HTTP_409_CONFLICT,
            code="recognition_not_running",
        ) from exc
    return APIResponse.ok(
        data=RecognitionStatus(**snapshot), message="Recognition runtime stopping"
    )


@router.get(
    "/status",
    response_model=APIResponse[RecognitionStatus],
    dependencies=[Depends(require_faculty_or_admin)],
)
def get_status(request: Request) -> APIResponse[RecognitionStatus]:
    snapshot = recognition_service.get_status(request.app.state)
    return APIResponse.ok(data=RecognitionStatus(**snapshot))
