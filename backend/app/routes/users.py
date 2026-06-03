"""Admin-only user management endpoints.

VisionAttend enforces a single-admin model. All mutation endpoints target
faculty accounts only; the service layer rejects operations on the
admin account with 403.
"""
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import CurrentUser, DBSession, require_admin, require_faculty_or_admin
from app.core.exceptions import AppException
from app.database.schemas.auth_schema import AdminResetPasswordRequest
from app.database.schemas.faculty_class_schema import (
    FacultyClassAssignment,
    FacultyClassesResponse,
    FacultyClassesUpdate,
)
from app.database.schemas.response import APIResponse
from app.database.schemas.user_schema import (
    CreateFacultyRequest,
    ToggleActiveRequest,
    UpdateFacultyRequest,
    UserListResponse,
    UserOut,
)
from app.services import faculty_class_service, user_service


router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=APIResponse[UserListResponse],
    dependencies=[Depends(require_admin)],
)
def list_users(
    db: DBSession,
    role: str | None = Query(None, description="Filter by role (admin, faculty)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> APIResponse[UserListResponse]:
    users, total = user_service.list_users(db, role=role, skip=skip, limit=limit)
    return APIResponse.ok(
        data=UserListResponse(
            users=[UserOut.model_validate(u) for u in users],
            total=total,
        )
    )


@router.post(
    "/faculty",
    response_model=APIResponse[UserOut],
    dependencies=[Depends(require_admin)],
)
def create_faculty(
    payload: CreateFacultyRequest,
    db: DBSession,
) -> APIResponse[UserOut]:
    user = user_service.create_faculty(
        db,
        username=payload.username,
        email=payload.email,
        password=payload.password,
    )
    return APIResponse.ok(data=UserOut.model_validate(user), message="Faculty user created")


@router.patch(
    "/{user_id}",
    response_model=APIResponse[UserOut],
    dependencies=[Depends(require_admin)],
)
def update_faculty(
    user_id: int,
    payload: UpdateFacultyRequest,
    db: DBSession,
) -> APIResponse[UserOut]:
    user = user_service.update_faculty(
        db,
        user_id,
        username=payload.username,
        email=payload.email,
        password=payload.password,
    )
    return APIResponse.ok(data=UserOut.model_validate(user), message="Faculty user updated")


@router.patch(
    "/{user_id}/active",
    response_model=APIResponse[UserOut],
    dependencies=[Depends(require_admin)],
)
def toggle_active(
    user_id: int,
    payload: ToggleActiveRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[UserOut]:
    if user_id == current_user.id and not payload.active:
        raise AppException(
            "Cannot deactivate your own account",
            status_code=400,
            code="self_deactivation",
        )
    user = user_service.toggle_active(db, user_id, active=payload.active)
    action = "activated" if payload.active else "deactivated"
    return APIResponse.ok(data=UserOut.model_validate(user), message=f"User {action}")


@router.delete(
    "/{user_id}",
    response_model=APIResponse,
    dependencies=[Depends(require_admin)],
)
def delete_faculty(
    user_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    if user_id == current_user.id:
        raise AppException(
            "Cannot delete your own account",
            status_code=400,
            code="self_deletion",
        )
    user_service.delete_faculty(db, user_id)
    return APIResponse.ok(message="Faculty user deleted")


@router.post(
    "/{user_id}/reset-password",
    response_model=APIResponse[UserOut],
    dependencies=[Depends(require_admin)],
)
def reset_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    db: DBSession,
) -> APIResponse[UserOut]:
    user = user_service.reset_password(db, user_id, new_password=payload.new_password)
    return APIResponse.ok(
        data=UserOut.model_validate(user),
        message="Password reset — user must change on next login",
    )


# ---------------------------------------------------------------------------
# Faculty ↔ class assignments
# ---------------------------------------------------------------------------

@router.get(
    "/{user_id}/classes",
    response_model=APIResponse[FacultyClassesResponse],
)
def get_faculty_classes(
    user_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[FacultyClassesResponse]:
    # Faculty can read their own classes; admin can read anyone's.
    if current_user.role != "admin" and current_user.id != user_id:
        raise AppException(
            "You can only view your own class assignments",
            status_code=403,
            code="forbidden",
        )
    assignments = faculty_class_service.get_assignments(db, user_id)
    return APIResponse.ok(
        data=FacultyClassesResponse(
            user_id=user_id,
            assignments=[FacultyClassAssignment(**a) for a in assignments],
        )
    )


@router.put(
    "/{user_id}/classes",
    response_model=APIResponse[FacultyClassesResponse],
    dependencies=[Depends(require_admin)],
)
def set_faculty_classes(
    user_id: int,
    payload: FacultyClassesUpdate,
    db: DBSession,
) -> APIResponse[FacultyClassesResponse]:
    assignments = faculty_class_service.set_assignments(db, user_id, payload.class_ids)
    return APIResponse.ok(
        data=FacultyClassesResponse(
            user_id=user_id,
            assignments=[FacultyClassAssignment(**a) for a in assignments],
        ),
        message="Class assignments updated",
    )
