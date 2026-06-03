"""Haar-cascade face detection.

Single responsibility: take a grayscale frame, return bounding boxes.
No model loading, no recognition, no I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple

from app.config.settings import settings


BoundingBox = Tuple[int, int, int, int]  # (x, y, w, h)


@dataclass
class FaceDetector:
    cascade: Any
    scale_factor: float
    min_neighbors: int

    @classmethod
    def load(cls) -> "FaceDetector":
        import cv2  # noqa: PLC0415 — lazy so backend boots without OpenCV

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            raise RuntimeError(f"Failed to load Haar cascade at {cascade_path}")
        return cls(
            cascade=cascade,
            scale_factor=settings.RECOGNITION_DETECT_SCALE_FACTOR,
            min_neighbors=settings.RECOGNITION_DETECT_MIN_NEIGHBORS,
        )

    def detect(self, gray_frame: Any) -> List[BoundingBox]:
        rects = self.cascade.detectMultiScale(
            gray_frame,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
        )
        # detectMultiScale returns an empty tuple when no faces are found.
        return [tuple(int(v) for v in r) for r in rects]

    def detect_largest(self, gray_frame: Any) -> "BoundingBox | None":
        """Return the single largest detected face, or None.

        Shared abstraction for capture and any future single-subject flow.
        Swapping Haar for YuNet later only requires replacing this class —
        callers that use detect_largest don't depend on cascade internals.
        """
        faces = self.detect(gray_frame)
        if not faces:
            return None
        return max(faces, key=lambda r: r[2] * r[3])
