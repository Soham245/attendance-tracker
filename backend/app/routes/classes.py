"""Academic class management routes (admin-only, except faculty list)."""
from typing import List

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.core.dependencies import DBSession, require_admin, require_faculty_or_admin
from app.database.schemas.class_schema import (
    ClassCreate,
    ClassListResponse,
    ClassResponse,
    ClassUpdate,
)
from app.database.schemas.response import APIResponse
from app.services import class_service


router = APIRouter(prefix="/classes", tags=["Academic Classes"])


class ClassFacultyItem(BaseModel):
    user_id: int
    username: str


class ClassFacultyResponse(BaseModel):
    class_id: int
    faculty: List[ClassFacultyItem]


@router.get(
    "",
    response_model=APIResponse[ClassListResponse],
    dependencies=[Depends(require_admin)],
)
def list_classes(
    db: DBSession,
    active_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> APIResponse[ClassListResponse]:
    items, total = class_service.list_classes(
        db, active_only=active_only, skip=skip, limit=limit
    )
    return APIResponse.ok(
        data=ClassListResponse(
            items=[ClassResponse.model_validate(c) for c in items],
            total=total,
        )
    )


@router.get(
    "/{class_id}",
    response_model=APIResponse[ClassResponse],
    dependencies=[Depends(require_admin)],
)
def get_class(db: DBSession, class_id: int) -> APIResponse[ClassResponse]:
    cls = class_service.get_class(db, class_id)
    return APIResponse.ok(data=ClassResponse.model_validate(cls))


@router.post(
    "",
    response_model=APIResponse[ClassResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_class(db: DBSession, body: ClassCreate) -> APIResponse[ClassResponse]:
    cls = class_service.create_class(db, body)
    return APIResponse.ok(
        data=ClassResponse.model_validate(cls),
        message=f"Class {cls.class_code} created",
    )


@router.patch(
    "/{class_id}",
    response_model=APIResponse[ClassResponse],
    dependencies=[Depends(require_admin)],
)
def update_class(
    db: DBSession, class_id: int, body: ClassUpdate
) -> APIResponse[ClassResponse]:
    cls = class_service.update_class(db, class_id, body)
    return APIResponse.ok(
        data=ClassResponse.model_validate(cls),
        message=f"Class {cls.class_code} updated",
    )


@router.delete(
    "/{class_id}",
    response_model=APIResponse,
    dependencies=[Depends(require_admin)],
)
def delete_class(db: DBSession, class_id: int) -> APIResponse:
    class_service.delete_class(db, class_id)
    return APIResponse.ok(message="Class deleted")


@router.get(
    "/{class_id}/faculty",
    response_model=APIResponse[ClassFacultyResponse],
    dependencies=[Depends(require_faculty_or_admin)],
)
def list_class_faculty(db: DBSession, class_id: int) -> APIResponse[ClassFacultyResponse]:
    """List faculty assigned to a class."""
    faculty = class_service.get_class_faculty(db, class_id)
    return APIResponse.ok(
        data=ClassFacultyResponse(
            class_id=class_id,
            faculty=faculty,
        )
    )
