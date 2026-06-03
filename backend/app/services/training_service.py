"""Model training / enrollment pipeline.

Runs synchronously inside a background thread spawned by the route. State is
tracked on ``app.state.training_state``; concurrency is gated by
``app.state.training_lock``. The pipeline is filesystem-driven — dataset
folders are the source of truth.

Backend dispatch:
  - **LBPH** (``RECOGNITION_BACKEND=lbph``): classic OpenCV training.
    Loads all images as grayscale, trains ``LBPHFaceRecognizer``, writes
    ``trainer.yml``.
  - **ArcFace** (``RECOGNITION_BACKEND=arcface``): embedding enrollment.
    Detects faces with YuNet, aligns via 5-point landmarks, extracts 512-d
    embeddings with the ArcFace ONNX model, builds a cosine-search gallery
    saved as ``gallery.npz``.

Both paths share: scan datasets → process → write artifacts → promote → reset flags.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logging import get_logger
from app.database.db import SessionLocal
from app.database.models.student import Student
from app.recognition import model_manager
from app.recognition.preprocess import prepare_face
from app.storage.local import (
    GALLERY_FILENAME,
    METADATA_FILENAME,
    TRAINER_FILENAME,
    list_student_images,
    student_dataset_path,
)


logger = get_logger("attendai.training")


STATE_IDLE = "idle"
STATE_RUNNING = "running"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"


def initial_state() -> Dict[str, Any]:
    return {
        "state": STATE_IDLE,
        "last_run_at": None,
        "last_error": None,
        "student_count": 0,
        "image_count": 0,
        "skipped_images": 0,
    }


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

@dataclass
class _ScanResult:
    images: List[Any]
    labels: List[int]
    student_records: Dict[int, Dict[str, Any]]
    skipped: int
    # For ArcFace enrollment: (student_id, filename, bgr_image) triples.
    bgr_entries: List[Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.bgr_entries is None:
            self.bgr_entries = []


def _scan_datasets_lbph(db: Session) -> _ScanResult:
    """Walk the filesystem and load grayscale images for LBPH training."""
    import cv2  # noqa: PLC0415

    images: List[Any] = []
    labels: List[int] = []
    student_records: Dict[int, Dict[str, Any]] = {}
    skipped = 0

    students = db.execute(
        select(Student).where(Student.status == "active").order_by(Student.id)
    ).scalars().all()
    for student in students:
        files = list_student_images(student.id)
        if not files:
            continue
        folder = student_dataset_path(student.id)
        added = 0
        for filename, _ in files:
            path = folder / filename
            gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if gray is None:
                skipped += 1
                logger.warning("Skipped unreadable image: %s", path)
                continue
            images.append(prepare_face(gray))
            labels.append(student.id)
            added += 1
        if added > 0:
            student_records[student.id] = {
                "id": student.id,
                "name": student.name,
                "roll_number": student.roll_number,
                "image_count": added,
            }
    return _ScanResult(images, labels, student_records, skipped)


def _scan_datasets_arcface(db: Session) -> _ScanResult:
    """Walk the filesystem and load BGR images for ArcFace enrollment."""
    import cv2  # noqa: PLC0415

    labels: List[int] = []
    student_records: Dict[int, Dict[str, Any]] = {}
    bgr_entries: List[Any] = []  # (student_id, filename, bgr_image)
    skipped = 0

    students = db.execute(
        select(Student).where(Student.status == "active").order_by(Student.id)
    ).scalars().all()
    for student in students:
        files = list_student_images(student.id)
        if not files:
            continue
        folder = student_dataset_path(student.id)
        added = 0
        for filename, _ in files:
            path = folder / filename
            bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if bgr is None:
                skipped += 1
                logger.warning("Skipped unreadable image: %s", path)
                continue
            bgr_entries.append((student.id, filename, bgr))
            labels.append(student.id)
            added += 1
        if added > 0:
            student_records[student.id] = {
                "id": student.id,
                "name": student.name,
                "roll_number": student.roll_number,
                "image_count": added,
            }
    return _ScanResult(
        images=[], labels=labels, student_records=student_records,
        skipped=skipped, bgr_entries=bgr_entries,
    )


def _reset_training_flags(db: Session, student_ids: List[int]) -> None:
    if not student_ids:
        return
    students = (
        db.execute(select(Student).where(Student.id.in_(student_ids))).scalars().all()
    )
    for s in students:
        s.training_required = False
    db.commit()


# ---------------------------------------------------------------------------
# LBPH training
# ---------------------------------------------------------------------------

def _train_lbph(images: List[Any], labels: List[int]) -> Any:
    import cv2  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(images, np.array(labels, dtype=np.int32))
    return recognizer


def _run_lbph(app_state: Any) -> None:
    started_at = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        scan = _scan_datasets_lbph(db)
        if not scan.images:
            raise RuntimeError("No training data found")

        candidate = model_manager.prepare_candidate()
        recognizer = _train_lbph(scan.images, scan.labels)
        recognizer.save(str(candidate / TRAINER_FILENAME))

        metadata = {
            "trained_at": started_at.isoformat(),
            "backend": "lbph",
            "student_count": len(scan.student_records),
            "image_count": len(scan.images),
            "student_ids": sorted(scan.student_records.keys()),
            "skipped_images": scan.skipped,
        }
        model_manager.write_artifacts(
            candidate, labels=scan.student_records, metadata=metadata
        )
        version_id = model_manager.promote_candidate()
        _reset_training_flags(db, list(scan.student_records.keys()))

        app_state.training_state = {
            "state": STATE_COMPLETED,
            "last_run_at": started_at.isoformat(),
            "last_error": None,
            "student_count": len(scan.student_records),
            "image_count": len(scan.images),
            "skipped_images": scan.skipped,
            "version": version_id,
        }
        logger.info(
            "LBPH training complete: version=%s students=%d images=%d skipped=%d",
            version_id, len(scan.student_records), len(scan.images), scan.skipped,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("LBPH training failed: %s", exc)
        app_state.training_state = {
            **app_state.training_state,
            "state": STATE_FAILED,
            "last_run_at": started_at.isoformat(),
            "last_error": str(exc),
        }
    finally:
        db.close()
        app_state.training_lock.release()


# ---------------------------------------------------------------------------
# ArcFace enrollment
# ---------------------------------------------------------------------------

def _run_arcface(app_state: Any) -> None:
    """Enrollment pipeline: detect → align → embed → gallery → promote."""
    import cv2  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    import onnxruntime as ort  # noqa: PLC0415

    from app.recognition.alignment import align_face, align_face_from_bbox
    from app.recognition.backends.arcface_backend import GALLERY_FILENAME as _GF
    from app.recognition.detectors.model_downloader import ensure_arcface_model
    from app.recognition.detectors.yunet_detector import YuNetDetectorBackend
    from app.recognition.gallery import EmbeddingGallery, GalleryEntry

    started_at = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        # 1. Load models.
        logger.info("ArcFace enrollment: loading models…")
        arcface_path = ensure_arcface_model()
        session = ort.InferenceSession(
            str(arcface_path), providers=["CPUExecutionProvider"]
        )
        input_name = session.get_inputs()[0].name
        detector = YuNetDetectorBackend.load()

        # 2. Scan datasets (BGR images).
        scan = _scan_datasets_arcface(db)
        if not scan.bgr_entries:
            raise RuntimeError("No enrollment data found")

        # 3. Detect, align, embed each image.
        entries: List[GalleryEntry] = []
        skipped_no_face = 0
        for student_id, filename, bgr in scan.bgr_entries:
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            dets = detector.detect(gray)
            if not dets:
                skipped_no_face += 1
                logger.debug("No face detected in %s for student %d", filename, student_id)
                # Fallback: use the whole image as a face (datasets are face crops).
                aligned = cv2.resize(bgr, (112, 112))
            else:
                det = max(dets, key=lambda d: d.bbox[2] * d.bbox[3])
                if det.landmarks is not None:
                    aligned = align_face(bgr, det.landmarks)
                else:
                    aligned = align_face_from_bbox(bgr, det.bbox)

            # ArcFace preprocessing: BGR→RGB, normalise to [-1, 1], NCHW.
            rgb = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB).astype(np.float32)
            blob = np.transpose((rgb / 127.5) - 1.0, (2, 0, 1))[np.newaxis, ...]

            # Forward pass.
            embedding = session.run(None, {input_name: blob})[0].flatten().astype(np.float32)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            entries.append(GalleryEntry(
                student_id=student_id,
                embedding=embedding,
                image_source=filename,
            ))

        if not entries:
            raise RuntimeError("No embeddings extracted")

        # 4. Build gallery and write artifacts.
        gallery = EmbeddingGallery(entries)
        candidate = model_manager.prepare_candidate()
        gallery.save(candidate / _GF)

        # Write a dummy trainer.yml so has_active_model() recognises the version.
        # The ArcFace backend reads gallery.npz, not trainer.yml, but the
        # model_manager checks for trainer.yml as the "model exists" sentinel.
        # We write a small placeholder to satisfy that check.
        (candidate / TRAINER_FILENAME).write_text(
            "# ArcFace embedding model — see gallery.npz\n", encoding="utf-8"
        )

        metadata = {
            "trained_at": started_at.isoformat(),
            "backend": "arcface",
            "student_count": len(scan.student_records),
            "image_count": len(scan.bgr_entries),
            "embedding_count": gallery.size,
            "student_ids": sorted(scan.student_records.keys()),
            "skipped_images": scan.skipped,
            "skipped_no_face": skipped_no_face,
            "arcface_model": settings.ARCFACE_MODEL_NAME,
        }
        model_manager.write_artifacts(
            candidate, labels=scan.student_records, metadata=metadata
        )
        version_id = model_manager.promote_candidate()
        _reset_training_flags(db, list(scan.student_records.keys()))

        app_state.training_state = {
            "state": STATE_COMPLETED,
            "last_run_at": started_at.isoformat(),
            "last_error": None,
            "student_count": len(scan.student_records),
            "image_count": len(scan.bgr_entries),
            "skipped_images": scan.skipped + skipped_no_face,
            "version": version_id,
        }
        logger.info(
            "ArcFace enrollment complete: version=%s students=%d embeddings=%d "
            "skipped=%d no_face=%d",
            version_id, len(scan.student_records), gallery.size,
            scan.skipped, skipped_no_face,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("ArcFace enrollment failed: %s", exc)
        app_state.training_state = {
            **app_state.training_state,
            "state": STATE_FAILED,
            "last_run_at": started_at.isoformat(),
            "last_error": str(exc),
        }
    finally:
        db.close()
        app_state.training_lock.release()


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def _run(app_state: Any) -> None:
    """Worker body — dispatches to the appropriate backend pipeline."""
    backend = settings.RECOGNITION_BACKEND.lower()
    if backend == "arcface":
        _run_arcface(app_state)
    else:
        _run_lbph(app_state)


def trigger_training(app_state: Any) -> Dict[str, Any]:
    """Kick off training in a background thread. Returns the new status snapshot.

    Raises RuntimeError if a training run is already in progress.
    """
    acquired = app_state.training_lock.acquire(blocking=False)
    if not acquired:
        raise RuntimeError("Training already in progress")

    app_state.training_state = {
        **app_state.training_state,
        "state": STATE_RUNNING,
        "last_error": None,
    }
    thread = threading.Thread(
        target=_run, args=(app_state,), name="attendai-training", daemon=True
    )
    thread.start()
    return app_state.training_state


def get_status(app_state: Any) -> Dict[str, Any]:
    return dict(app_state.training_state)


def get_active_model_metadata() -> Dict[str, Any] | None:
    return model_manager.get_active_metadata()


__all__ = [
    "STATE_IDLE",
    "STATE_RUNNING",
    "STATE_COMPLETED",
    "STATE_FAILED",
    "initial_state",
    "trigger_training",
    "get_status",
    "get_active_model_metadata",
    "METADATA_FILENAME",
]
