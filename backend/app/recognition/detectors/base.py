"""Face detector protocol and unified detection result.

Every detection backend (Haar cascade, YuNet, future alternatives) must
conform to `FaceDetectorBackend`. The protocol carries optional 5-point
facial landmarks — Haar doesn't produce them, but YuNet and DNN-based
detectors do. ArcFace alignment requires landmarks, so the pipeline can
check `result.landmarks is not None` to decide whether alignment is possible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol, Tuple, runtime_checkable


BoundingBox = Tuple[int, int, int, int]  # (x, y, w, h)


@dataclass(frozen=True)
class DetectionResult:
    """One detected face with optional metadata.

    Attributes:
        bbox:        (x, y, w, h) pixel bounding box.
        confidence:  Detector confidence in [0, 1]. Haar cascades don't
                     produce a native score, so the Haar adapter sets 1.0.
        landmarks:   Optional 5-point facial landmarks [(x,y), ...]:
                     left eye, right eye, nose tip, left mouth, right mouth.
                     Required for ArcFace alignment; None for Haar.
    """

    bbox: BoundingBox
    confidence: float = 1.0
    landmarks: Optional[List[Tuple[int, int]]] = field(default=None)


@runtime_checkable
class FaceDetectorBackend(Protocol):
    """Structural interface for face detection backends."""

    @property
    def backend_name(self) -> str:
        """Short identifier, e.g. ``"haar"`` or ``"yunet"``."""
        ...

    def detect(self, gray_frame: Any) -> List[DetectionResult]:
        """Return all detected faces as `DetectionResult` instances."""
        ...

    def detect_largest(self, gray_frame: Any) -> Optional[DetectionResult]:
        """Return the single largest detected face, or None."""
        ...
