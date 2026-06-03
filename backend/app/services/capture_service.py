"""Public surface for the dataset capture runtime.

Routes call into this service; the camera + frame loop live in
`app.recognition.capture_runtime`. This file owns:

    - input validation (student exists, target in range)
    - runtime coexistence checks (capture vs recognition: only one camera)
    - sample persistence (delegating to the storage layer)
    - post-capture DB updates (`training_required = True`)

Strict layering: this service must NOT import recognition inference,
training logic, or attendance logic.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import status

from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.database.db import SessionLocal
from app.database.models.student import Student
from app.recognition import capture_runtime, runtime as recognition_runtime
from app.services.student_service import get_student
from app.storage.local import (
    ensure_student_dataset,
    list_student_images,
    remove_student_dataset,
    write_student_image,
)
from sqlalchemy.orm import Session


logger = get_logger("attendai.capture.service")


def _ensure_camera_free(app_state: Any) -> None:
    """Reject if any other runtime currently owns the webcam.

    Capture and recognition both compete for `cv2.VideoCapture(0)`; running
    both at once corrupts the camera state on every OS we've seen. Each
    runtime holds its own lock; we check the *other* one's state here.
    """
    rec_state = app_state.recognition_runtime["state"]
    if rec_state in (
        recognition_runtime.STATE_STARTING,
        recognition_runtime.STATE_RUNNING,
        recognition_runtime.STATE_STOPPING,
    ):
        raise AppException(
            "Recognition runtime is using the camera. Stop it before capturing.",
            status_code=status.HTTP_409_CONFLICT,
            code="camera_in_use",
        )


def _make_sample_writer(student_id: int):
    """Return a writer callable bound to a student folder.

    Called from the capture worker thread. Each invocation persists one
    processed JPEG to disk under the student's dataset folder using a UUID
    filename so it can never collide with manually uploaded images.
    """
    ensure_student_dataset(student_id)

    def write(jpeg_bytes: bytes, _sample_index: int) -> str:
        stored_name = f"capture_{uuid.uuid4().hex}.jpg"
        write_student_image(student_id, stored_name, jpeg_bytes)
        return stored_name

    return write


def _mark_training_required(student_id: int, samples_collected: int) -> None:
    """Post-capture hook: flip the student's training flag.

    Runs in the worker thread, so it opens its own short-lived DB session.
    Never triggers training itself — that stays an explicit admin action.
    """
    db: Session = SessionLocal()
    try:
        student = db.get(Student, student_id)
        if student is None:
            logger.warning(
                "Capture completed for missing student_id=%s; skipping flag update",
                student_id,
            )
            return
        student.training_required = True
        db.commit()
        logger.info(
            "Marked student_id=%s training_required=True after %d samples",
            student_id, samples_collected,
        )
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("Failed to set training_required after capture")
    finally:
        db.close()


def _reset_student_dataset(student_id: int) -> int:
    """Remove all existing dataset images for a student.

    Called before capture starts when re-enrolling. Returns the number of
    images that were removed. The folder is recreated empty by the sample
    writer.
    """
    existing = list_student_images(student_id)
    count = len(existing)
    if count > 0:
        remove_student_dataset(student_id)
        logger.info(
            "Reset dataset for student_id=%s (removed %d images)",
            student_id, count,
        )
    return count


# -- public API --------------------------------------------------------------


def start_capture(
    db: Session,
    app_state: Any,
    *,
    student_id: int,
    replace: bool = False,
) -> Dict[str, Any]:
    """Validate inputs, ensure camera availability, spawn the capture worker.

    When *replace* is True the student's existing dataset images are wiped
    before capture begins so the new session produces a clean dataset.
    """
    student = get_student(db, student_id)  # 404 if missing
    _ensure_camera_free(app_state)

    if replace:
        removed = _reset_student_dataset(student.id)
        if removed:
            student.training_required = True
            db.commit()
            logger.info(
                "Cleared %d old images for student_id=%s before re-enrollment",
                removed, student.id,
            )

    try:
        snapshot = capture_runtime.start(
            app_state,
            student_id=student.id,
            target_samples=0,  # ignored; runtime computes from phases
            sample_writer=_make_sample_writer(student.id),
            on_complete=_mark_training_required,
        )
    except RuntimeError as exc:
        raise AppException(
            str(exc),
            status_code=status.HTTP_409_CONFLICT,
            code="capture_already_running",
        ) from exc
    return snapshot


def stop_capture(app_state: Any) -> Dict[str, Any]:
    try:
        return capture_runtime.stop(app_state)
    except RuntimeError as exc:
        raise AppException(
            str(exc),
            status_code=status.HTTP_409_CONFLICT,
            code="capture_not_running",
        ) from exc


def get_status(app_state: Any) -> Dict[str, Any]:
    return capture_runtime.get_status(app_state)


def get_status_with_dataset_size(db: Session, app_state: Any) -> Dict[str, Any]:
    """Status snapshot enriched with the on-disk dataset size for the active
    or most-recent student. Pure read; safe to call from a polling endpoint."""
    snapshot = get_status(app_state)
    student_id = snapshot.get("student_id")
    if student_id is not None:
        snapshot["dataset_image_count"] = len(list_student_images(student_id))
    else:
        snapshot["dataset_image_count"] = 0
    return snapshot
