"""LBPH inference + label resolution + threshold evaluation.

Reads exclusively from `storage/models/active/`. Never touches candidate or
backup slots, never trains, never mutates files.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from app.config.settings import settings
from app.recognition import model_manager
from app.storage.local import TRAINER_FILENAME


@dataclass
class FaceRecognizer:
    model: Any
    labels: Dict[str, Dict[str, Any]]
    threshold: float

    @classmethod
    def load_active(cls) -> "FaceRecognizer":
        import cv2  # noqa: PLC0415

        if not model_manager.has_active_model():
            raise FileNotFoundError("No active model")

        trainer_path = model_manager.active_dir() / TRAINER_FILENAME
        model = cv2.face.LBPHFaceRecognizer_create()
        model.read(str(trainer_path))

        return cls(
            model=model,
            labels=model_manager.get_active_labels() or {},
            threshold=settings.RECOGNITION_CONFIDENCE_THRESHOLD,
        )

    def predict(self, face_gray: Any) -> Optional[Tuple[int, float]]:
        """Return (student_id, confidence) for a confident match, else None.

        LBPH `predict` returns a distance — lower is a stronger match. A
        distance above `threshold` is treated as unknown.
        """
        label, distance = self.model.predict(face_gray)
        if distance > self.threshold:
            return None
        return int(label), float(distance)

    def label_info(self, student_id: int) -> Optional[Dict[str, Any]]:
        return self.labels.get(str(student_id))
