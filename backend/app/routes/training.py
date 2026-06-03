from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import require_admin, require_faculty_or_admin
from app.core.exceptions import AppException
from app.database.schemas.response import APIResponse
from app.database.schemas.training_schema import (
    ModelMetadata,
    ModelVersionList,
    TrainingStatus,
)
from app.recognition import model_manager
from app.services import training_service


router = APIRouter(prefix="/training", tags=["Training"])


@router.post(
    "/run",
    response_model=APIResponse[TrainingStatus],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_admin)],
)
def trigger_run(request: Request) -> APIResponse[TrainingStatus]:
    try:
        snapshot = training_service.trigger_training(request.app.state)
    except RuntimeError as exc:
        raise AppException(
            str(exc),
            status_code=status.HTTP_409_CONFLICT,
            code="training_in_progress",
        ) from exc
    return APIResponse.ok(
        data=TrainingStatus(**snapshot), message="Training started"
    )


@router.get(
    "/status",
    response_model=APIResponse[TrainingStatus],
    dependencies=[Depends(require_faculty_or_admin)],
)
def get_status(request: Request) -> APIResponse[TrainingStatus]:
    snapshot = training_service.get_status(request.app.state)
    return APIResponse.ok(data=TrainingStatus(**snapshot))


@router.get(
    "/model",
    response_model=APIResponse[ModelMetadata],
    dependencies=[Depends(require_faculty_or_admin)],
)
def get_model_metadata() -> APIResponse[ModelMetadata]:
    meta = training_service.get_active_model_metadata()
    if meta is None:
        raise AppException(
            "No active model",
            status_code=status.HTTP_404_NOT_FOUND,
            code="no_active_model",
        )
    return APIResponse.ok(data=ModelMetadata(**meta))


@router.get(
    "/versions",
    response_model=APIResponse[ModelVersionList],
    dependencies=[Depends(require_faculty_or_admin)],
)
def get_versions() -> APIResponse[ModelVersionList]:
    """List all retained model versions (newest first)."""
    versions = model_manager.list_versions()
    reg = model_manager._read_registry()
    return APIResponse.ok(
        data=ModelVersionList(
            versions=versions,
            active_version=reg.active_version,
        )
    )


@router.post(
    "/rollback/{version_id}",
    response_model=APIResponse[ModelVersionList],
    dependencies=[Depends(require_admin)],
)
def rollback_model(version_id: str) -> APIResponse[ModelVersionList]:
    """Roll back the active model to a previous version."""
    try:
        model_manager.rollback(version_id)
    except ValueError as exc:
        raise AppException(
            str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_version",
        ) from exc
    except FileNotFoundError as exc:
        raise AppException(
            str(exc),
            status_code=status.HTTP_404_NOT_FOUND,
            code="version_not_found",
        ) from exc

    versions = model_manager.list_versions()
    reg = model_manager._read_registry()
    return APIResponse.ok(
        data=ModelVersionList(
            versions=versions,
            active_version=reg.active_version,
        ),
        message=f"Rolled back to {version_id}",
    )


@router.delete(
    "/versions/{version_id}",
    response_model=APIResponse[ModelVersionList],
    dependencies=[Depends(require_admin)],
)
def delete_version(version_id: str) -> APIResponse[ModelVersionList]:
    """Delete a single non-active model version."""
    try:
        model_manager.delete_version(version_id)
    except ValueError as exc:
        raise AppException(
            str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_version",
        ) from exc

    versions = model_manager.list_versions()
    reg = model_manager._read_registry()
    return APIResponse.ok(
        data=ModelVersionList(
            versions=versions,
            active_version=reg.active_version,
        ),
        message=f"Deleted version {version_id}",
    )


@router.delete(
    "/versions",
    response_model=APIResponse,
    dependencies=[Depends(require_admin)],
)
def drop_all_models() -> APIResponse:
    """Delete ALL model versions and reset the version counter."""
    count = model_manager.drop_all_models()
    return APIResponse.ok(
        message=f"Dropped {count} model version{'s' if count != 1 else ''}; registry reset",
    )
