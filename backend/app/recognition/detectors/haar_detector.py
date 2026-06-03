"""Haar cascade adapter — wraps the existing FaceDetector as a backend.

Haar cascades produce bounding boxes but no confidence score and no facial
landmarks. The adapter fills ``confidence=1.0`` (no native score available)
and ``landmarks=None`` so the pipeline knows alignment is not possible with
this detector.
"""
from __future__ import annotations

from typing import Any, List, Optional

from app.recognition.detector import FaceDetector
from app.recognition.detectors.base import (
    BoundingBox,
    DetectionResult,
    FaceDetectorBackend,
)


class HaarDetectorBackend:
    """Wraps `FaceDetector` to satisfy `FaceDetectorBackend`."""

    def __init__(self, detector: FaceDetector) -> None:
        self._det = detector

    @classmethod
    def load(cls) -> "HaarDetectorBackend":
        return cls(detector=FaceDetector.load())

    # -- FaceDetectorBackend interface ----------------------------------------

    @property
    def backend_name(self) -> str:
        return "haar"

    def detect(self, gray_frame: Any) -> List[DetectionResult]:
        raw_bboxes: List[BoundingBox] = self._det.detect(gray_frame)
        return [
            DetectionResult(bbox=bb, confidence=1.0, landmarks=None)
            for bb in raw_bboxes
        ]

    def detect_largest(self, gray_frame: Any) -> Optional[DetectionResult]:
        bb = self._det.detect_largest(gray_frame)
        if bb is None:
            return None
        return DetectionResult(bbox=bb, confidence=1.0, landmarks=None)
