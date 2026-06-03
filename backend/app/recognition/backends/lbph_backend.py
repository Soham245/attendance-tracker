"""LBPH adapter — wraps the existing FaceRecognizer as a RecognizerBackend.

LBPH's `predict()` returns a *distance* (lower = better). This adapter
converts that into the unified *similarity* scale [0, 1] (higher = better)
so downstream code never sees backend-specific polarity.

Conversion formula:
    similarity = clamp(1 - distance / scale, 0, 1)

Where `scale` (`LBPH_DISTANCE_SCALE` in settings) defines the distance that
maps to similarity 0.0. Any distance >= scale is clamped to 0.0; a distance
of 0 maps to 1.0.

The original distance threshold is also converted: the LBPH ceiling
(`RECOGNITION_CONFIDENCE_THRESHOLD`) becomes a similarity floor.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.config.settings import settings
from app.recognition.backends.base import Prediction, RecognizerBackend
from app.recognition.recognizer import FaceRecognizer


class LBPHBackend:
    """Wraps `FaceRecognizer` to satisfy `RecognizerBackend`."""

    def __init__(
        self,
        recognizer: FaceRecognizer,
        distance_scale: float | None = None,
    ) -> None:
        self._rec = recognizer
        self._scale = (
            distance_scale
            if distance_scale is not None
            else settings.LBPH_DISTANCE_SCALE
        )

    @classmethod
    def load_active(cls) -> "LBPHBackend":
        """Construct from the currently active LBPH model."""
        return cls(recognizer=FaceRecognizer.load_active())

    # -- RecognizerBackend interface ------------------------------------------

    @property
    def backend_name(self) -> str:
        return "lbph"

    @property
    def similarity_threshold(self) -> float:
        """Convert the LBPH distance ceiling into a similarity floor."""
        return max(0.0, 1.0 - self._rec.threshold / self._scale)

    def predict(self, face_crop: Any) -> Optional[Prediction]:
        result = self._rec.predict(face_crop)
        if result is None:
            return None
        student_id, distance = result
        similarity = max(0.0, min(1.0, 1.0 - distance / self._scale))
        return Prediction(
            student_id=student_id,
            similarity=round(similarity, 4),
            raw_metric=round(distance, 2),
            backend="lbph",
        )

    def label_info(self, student_id: int) -> Optional[Dict[str, Any]]:
        return self._rec.label_info(student_id)

