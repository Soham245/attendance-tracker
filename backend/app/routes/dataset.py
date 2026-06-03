from fastapi import APIRouter, Depends, File, UploadFile, status

from app.config.constants import API_TAG_STUDENTS
from app.core.dependencies import DBSession, require_admin, require_faculty_or_admin
from app.database.schemas.dataset_schema import (
    DatasetImageInfo,
    DatasetListResponse,
    DatasetUploadResponse,
)
from app.database.schemas.response import APIResponse
from app.services import dataset_service


router = APIRouter(
    prefix="/students/{student_id}/dataset",
    tags=[API_TAG_STUDENTS],
)


@router.post(
    "/images",
    response_model=APIResponse[DatasetUploadResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def upload_image(
    student_id: int,
    db: DBSession,
    file: UploadFile = File(...),
) -> APIResponse[DatasetUploadResponse]:
    data = await file.read()
    _, stored_name, count = dataset_service.register_image(
        db,
        student_id,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
    )
    return APIResponse.ok(
        data=DatasetUploadResponse(
            student_id=student_id,
            image=DatasetImageInfo(filename=stored_name, size_bytes=len(data)),
            image_count=count,
        ),
        message="Image registered",
    )


@router.get(
    "/images",
    response_model=APIResponse[DatasetListResponse],
    dependencies=[Depends(require_faculty_or_admin)],
)
def list_images(student_id: int, db: DBSession) -> APIResponse[DatasetListResponse]:
    files = dataset_service.list_images(db, student_id)
    return APIResponse.ok(
        data=DatasetListResponse(
            student_id=student_id,
            image_count=len(files),
            images=[DatasetImageInfo(filename=name, size_bytes=size) for name, size in files],
        )
    )


@router.delete(
    "/images",
    response_model=APIResponse[dict],
    dependencies=[Depends(require_admin)],
)
def delete_all_images(student_id: int, db: DBSession) -> APIResponse[dict]:
    deleted = dataset_service.delete_all_images(db, student_id)
    return APIResponse.ok(
        data={"student_id": student_id, "deleted_count": deleted, "image_count": 0},
        message=f"Deleted {deleted} image(s)",
    )


@router.delete(
    "/images/{filename}",
    response_model=APIResponse[dict],
    dependencies=[Depends(require_admin)],
)
def delete_image(
    student_id: int, filename: str, db: DBSession
) -> APIResponse[dict]:
    remaining = dataset_service.delete_image(db, student_id, filename)
    return APIResponse.ok(
        data={"student_id": student_id, "filename": filename, "image_count": remaining},
        message="Image deleted",
    )
