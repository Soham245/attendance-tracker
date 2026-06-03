"""Per-frame recognition pipeline: detect + recognize -> events.

Emits lightweight recognition events. No persistence, no duplicate checks,
no attendance logic — the attendance layer will consume these later.

The DB is the authoritative source of valid operational identities. A
confident model prediction for a student that no longer exists in the DB
is a stale-model artifact: the detection is annotated as such but NO
recognition event is produced — it must not enter the runtime's operational
pipeline (cooldown, attendance, recent feed).

Backend-agnostic: the pipeline receives a `RecognizerBackend` and a
`FaceDetectorBackend` — it never knows whether it's talking to LBPH or
ArcFace. All confidence values are expressed as **similarity** in [0, 1]
where higher = better match.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.recognition.alignment import align_face, align_face_from_bbox
from app.recognition.backends.base import Prediction, RecognizerBackend
from app.recognition.backends.lbph_backend import LBPHBackend
from app.recognition.detectors.base import DetectionResult, FaceDetectorBackend
from app.recognition.detectors.haar_detector import HaarDetectorBackend
from app.recognition.identity_validator import IdentityValidator, get_validator
from app.recognition.metrics import FrameTimings
from app.recognition.preprocess import prepare_face


@dataclass
class RecognitionEvent:
    student_id: int
    confidence: float  # unified similarity [0, 1]; higher = better
    recognized_at: str  # ISO 8601 UTC
    # Display identity copied from the active model's labels.json. Lets the
    # recent-recognitions feed render human-readable names without a DB hit
    # per event; the model is authoritative for what was matched, the DB is
    # still authoritative for whether emission was allowed (see validator).
    student_name: Optional[str] = None
    student_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Detection:
    """One detected face with its bounding box and optional recognition."""
    bbox: tuple  # (x, y, w, h)
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    confidence: Optional[float] = None  # unified similarity [0, 1]
    # True when the model predicted a student that is no longer in the DB.
    # Stale detections never produce events; they only drive the warning overlay.
    stale: bool = False


@dataclass
class FrameResult:
    """Full per-frame output: all detections (with bboxes) + emittable events."""
    detections: List[Detection]
    events: List[RecognitionEvent]
    stale_ids: List[int] = field(default_factory=list)
    timings: FrameTimings = field(default_factory=FrameTimings)


def _load_recognizer_backend() -> RecognizerBackend:
    """Factory: instantiate the configured recognition backend."""
    backend = settings.RECOGNITION_BACKEND.lower()
    if backend == "lbph":
        return LBPHBackend.load_active()
    if backend == "arcface":
        from app.recognition.backends.arcface_backend import ArcFaceBackend
        return ArcFaceBackend.load_active()
    raise ValueError(f"Unknown recognition backend: {backend!r}")


def _load_detector_backend() -> FaceDetectorBackend:
    """Factory: instantiate the configured detection backend."""
    backend = settings.DETECTION_BACKEND.lower()
    if backend == "haar":
        return HaarDetectorBackend.load()
    if backend == "yunet":
        from app.recognition.detectors.yunet_detector import YuNetDetectorBackend
        return YuNetDetectorBackend.load()
    raise ValueError(f"Unknown detection backend: {backend!r}")


@dataclass
class RecognitionPipeline:
    detector: FaceDetectorBackend
    recognizer: RecognizerBackend
    validator: IdentityValidator

    @classmethod
    def load_from_active(cls) -> "RecognitionPipeline":
        return cls(
            detector=_load_detector_backend(),
            recognizer=_load_recognizer_backend(),
            validator=get_validator(),
        )

    def process_frame(self, frame_bgr: Any) -> List[RecognitionEvent]:
        return self.process_frame_full(frame_bgr).events

    def process_frame_full(self, frame_bgr: Any) -> FrameResult:
        import cv2  # noqa: PLC0415

        t_frame_start = time.perf_counter()

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        detections: List[Detection] = []
        events: List[RecognitionEvent] = []
        stale_ids: List[int] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        is_embedding = self.recognizer.backend_name != "lbph"

        # -- Detection phase (timed as a batch) --
        t0 = time.perf_counter()
        det_results = list(self.detector.detect(gray))
        detection_ms = (time.perf_counter() - t0) * 1000.0

        align_ms_total = 0.0
        embed_ms_total = 0.0
        gallery_ms_total = 0.0

        for det_result in det_results:
            x, y, w, h = det_result.bbox

            # -- Alignment / preprocessing phase (timed per face) --
            t0 = time.perf_counter()
            if is_embedding:
                if det_result.landmarks is not None:
                    face = align_face(frame_bgr, det_result.landmarks)
                else:
                    face = align_face_from_bbox(frame_bgr, det_result.bbox)
            else:
                face = prepare_face(gray[y : y + h, x : x + w])
            align_ms_total += (time.perf_counter() - t0) * 1000.0

            # -- Recognition phase (embedding + gallery search) --
            # For embedding backends, predict() = embed + search internally.
            # We time the whole call; the runtime metrics distinguish the
            # backend type so operators know what the cost includes.
            t0 = time.perf_counter()
            prediction: Optional[Prediction] = self.recognizer.predict(face)
            predict_ms = (time.perf_counter() - t0) * 1000.0

            # For embedding backends, the predict call covers both embedding
            # extraction and gallery search. We attribute it as embedding+gallery.
            if is_embedding:
                embed_ms_total += predict_ms
            else:
                gallery_ms_total += predict_ms

            if prediction is None:
                detections.append(Detection(bbox=det_result.bbox))
                continue

            student_id = prediction.student_id
            similarity = prediction.similarity
            info = self.recognizer.label_info(student_id) or {}
            name = info.get("name")
            code = info.get("roll_number")

            if not self.validator.exists(student_id):
                detections.append(
                    Detection(
                        bbox=det_result.bbox,
                        student_id=student_id,
                        student_name=name,
                        confidence=similarity,
                        stale=True,
                    )
                )
                stale_ids.append(student_id)
                continue

            detections.append(
                Detection(
                    bbox=det_result.bbox,
                    student_id=student_id,
                    student_name=name,
                    confidence=similarity,
                )
            )
            events.append(
                RecognitionEvent(
                    student_id=student_id,
                    confidence=similarity,
                    recognized_at=now_iso,
                    student_name=name,
                    student_code=code,
                )
            )

        total_ms = (time.perf_counter() - t_frame_start) * 1000.0
        timings = FrameTimings(
            detection_ms=round(detection_ms, 2),
            alignment_ms=round(align_ms_total, 2),
            embedding_ms=round(embed_ms_total, 2),
            gallery_ms=round(gallery_ms_total, 2),
            total_ms=round(total_ms, 2),
            face_count=len(det_results),
        )

        return FrameResult(
            detections=detections,
            events=events,
            stale_ids=stale_ids,
            timings=timings,
        )
