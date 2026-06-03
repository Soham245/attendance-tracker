from fastapi import APIRouter

from app.config.constants import API_TAG_AUTH
from app.core.dependencies import CurrentUser, DBSession
from app.database.schemas.auth_schema import (
    ChangePasswordRequest,
    LoginRequest,
    TokenData,
    UserPublic,
)
from app.database.schemas.response import APIResponse
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=[API_TAG_AUTH])


@router.post("/login", response_model=APIResponse[TokenData])
def login(payload: LoginRequest, db: DBSession) -> APIResponse[TokenData]:
    _, token = auth_service.login(db, payload.username, payload.password)
    return APIResponse.ok(data=token, message="Login successful")


@router.get("/me", response_model=APIResponse[UserPublic])
def me(user: CurrentUser) -> APIResponse[UserPublic]:
    return APIResponse.ok(data=UserPublic.model_validate(user))


@router.post("/change-password", response_model=APIResponse[UserPublic])
def change_password(
    payload: ChangePasswordRequest,
    user: CurrentUser,
    db: DBSession,
) -> APIResponse[UserPublic]:
    if payload.new_password != payload.confirm_password:
        from app.core.exceptions import AppException
        from fastapi import status

        raise AppException(
            "New password and confirmation do not match",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="password_mismatch",
        )
    updated = auth_service.change_password(
        db, user, payload.current_password, payload.new_password
    )
    return APIResponse.ok(
        data=UserPublic.model_validate(updated),
        message="Password changed successfully",
    )
