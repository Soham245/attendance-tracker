from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import DBSession, require_faculty_or_admin
from app.core.exceptions import AppException
from app.database.models.user import User
from app.database.schemas.orchestration_schema import SessionStatus
from app.database.schemas.response import APIResponse
from app.database.schemas.session_schema import SessionStartRequest
from app.services import orchestration_service


router = APIRouter(prefix="/session", tags=["Session"])

# Annotated dependency that returns the current user after faculty-or-admin check.
FacultyOrAdmin = Annotated[User, Depends(require_faculty_or_admin)]


@router.post(
    "/start",
    response_model=APIResponse[SessionStatus],
    status_code=status.HTTP_202_ACCEPTED,
)
def start_session(
    body: SessionStartRequest,
    request: Request,
    db: DBSession,
    user: FacultyOrAdmin,
) -> APIResponse[SessionStatus]:
    try:
        snapshot = orchestration_service.start_session(
            request.app.state,
            db=db,
            class_id=body.class_id,
            faculty_id=user.id,
            session_name=body.session_name,
            is_admin=(user.role == "admin"),
        )
    except RuntimeError as exc:
        raise AppException(
            str(exc),
            status_code=status.HTTP_409_CONFLICT,
            code="session_already_active",
        ) from exc
    return APIResponse.ok(data=SessionStatus(**snapshot), message="Session starting")


@router.post(
    "/stop",
    response_model=APIResponse[SessionStatus],
    dependencies=[Depends(require_faculty_or_admin)],
)
def stop_session(request: Request) -> APIResponse[SessionStatus]:
    try:
        snapshot = orchestration_service.stop_session(request.app.state)
    except RuntimeError as exc:
        raise AppException(
            str(exc),
            status_code=status.HTTP_409_CONFLICT,
            code="session_not_active",
        ) from exc
    return APIResponse.ok(data=SessionStatus(**snapshot), message="Session stopping")


@router.get(
    "/status",
    response_model=APIResponse[SessionStatus],
    dependencies=[Depends(require_faculty_or_admin)],
)
def get_status(request: Request) -> APIResponse[SessionStatus]:
    snapshot = orchestration_service.get_status(request.app.state)
    return APIResponse.ok(data=SessionStatus(**snapshot))
