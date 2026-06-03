"""Dataset image registration.

Owns the lifecycle of student dataset images on the local filesystem:
upload validation, write, listing, and delete. No recognition, no training,
no preprocessing — those live in (future) recognition modules and read from
the folder owned by this service.
"""
import io
import uuid
from typing import List, Tuple

from fastapi import status
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.database.models.student import Student
from app.services.student_service import get_student
from app.storage.local import (
    list_student_images,
    resolve_student_image,
    write_student_image,
)


logger = get_logger("attendai.dataset")


ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}


def _extract_extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        raise AppException(
            "Filename must include an extension",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_filename",
        )
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise AppException(
            f"Unsupported file extension: .{ext}",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="unsupported_extension",
        )
    return "jpg" if ext == "jpeg" else ext  # normalize


def _validate_mime(content_type: str | None) -> None:
    if content_type not in ALLOWED_MIME_TYPES:
        raise AppException(
            f"Unsupported content type: {content_type}",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="unsupported_mime",
        )


def _validate_size(data: bytes) -> None:
    if len(data) == 0:
        raise AppException(
            "Empty upload",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="empty_upload",
        )
    if len(data) > settings.UPLOAD_MAX_BYTES:
        raise AppException(
            f"Upload exceeds {settings.UPLOAD_MAX_BYTES} bytes",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            code="upload_too_large",
        )


def _validate_image_integrity(data: bytes) -> Tuple[int, int]:
    try:
        # verify() consumes the stream — reopen for size.
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
    except (UnidentifiedImageError, OSError) as exc:
        raise AppException(
            "Corrupted or unreadable image",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="corrupt_image",
        ) from exc

    if min(width, height) < settings.IMAGE_MIN_DIMENSION:
        raise AppException(
            f"Image too small (min {settings.IMAGE_MIN_DIMENSION}px on each side)",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="image_too_small",
        )
    return width, height


def register_image(
    db: Session,
    student_id: int,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
) -> Tuple[Student, str, int]:
    """Validate + persist an image to the student's dataset folder.

    Returns (student, stored_filename, current_image_count).
    """
    student = get_student(db, student_id)  # 404s if missing

    ext = _extract_extension(filename)
    _validate_mime(content_type)
    _validate_size(data)
    _validate_image_integrity(data)

    # UUID filename — guarantees uniqueness, drops untrusted client name.
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    write_student_image(student_id, stored_name, data)

    student.training_required = True
    db.commit()
    db.refresh(student)

    image_count = len(list_student_images(student_id))
    logger.info(
        "Registered image student_id=%s filename=%s count=%s",
        student_id, stored_name, image_count,
    )
    return student, stored_name, image_count


def list_images(db: Session, student_id: int) -> List[Tuple[str, int]]:
    get_student(db, student_id)
    return list_student_images(student_id)


def delete_all_images(db: Session, student_id: int) -> int:
    """Remove every image in the student's dataset folder.

    Returns the number of images that were deleted.
    """
    student = get_student(db, student_id)
    images = list_student_images(student_id)
    count = len(images)
    if count == 0:
        return 0

    folder = resolve_student_image(student_id, images[0][0]).parent
    for name, _ in images:
        path = folder / name
        if path.is_file():
            path.unlink()

    student.training_required = True
    db.commit()
    logger.info("Deleted all %d images for student_id=%s", count, student_id)
    return count


def delete_image(db: Session, student_id: int, filename: str) -> int:
    student = get_student(db, student_id)
    try:
        path = resolve_student_image(student_id, filename)
    except ValueError as exc:
        raise AppException(
            "Invalid image filename",
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_filename",
        ) from exc

    if not path.is_file():
        raise AppException(
            "Image not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="image_not_found",
        )

    path.unlink()
    student.training_required = True
    db.commit()

    remaining = len(list_student_images(student_id))
    logger.info(
        "Deleted image student_id=%s filename=%s remaining=%s",
        student_id, filename, remaining,
    )
    return remaining
