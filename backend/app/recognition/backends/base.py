"""Recognition backend protocol and unified prediction result.

Every recognition backend (LBPH, ArcFace, future alternatives) must conform
to `RecognizerBackend`. The protocol enforces a unified `Prediction` output
where confidence is **always** expressed as similarity in [0, 1] with higher
values meaning a stronger match. Individual backends translate their native
metric (LBPH distance, cosine similarity, etc.) into this common scale.

This abstraction exists so `pipeline.py` and everything downstream (runtime,
frame tracker, diagnostics, frontend) never deal with backend-specific metric
polarity or value ranges.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class Prediction:
    """Unified prediction result from any recognition backend.

    Attributes:
        student_id:  The matched identity's database primary key.
        similarity:  Normalised confidence in [0.0, 1.0]; higher = better.
                     This is the ONLY metric downstream code should use.
        raw_metric:  The backend's native score before normalisation. Kept
                     for debugging and threshold-tuning telemetry only.
        backend:     Short tag identifying the backend (e.g. "lbph", "arcface").
    """

    student_id: int
    similarity: float
    raw_metric: float
    backend: str


@runtime_checkable
class RecognizerBackend(Protocol):
    """Structural interface that every recognition backend implements."""

    @property
    def backend_name(self) -> str:
        """Short identifier, e.g. ``"lbph"`` or ``"arcface"``."""
        ...

    @property
    def similarity_threshold(self) -> float:
        """Minimum similarity for a match. Below this the backend returns None."""
        ...

    def predict(self, face_crop: Any) -> Optional[Prediction]:
        """Run inference on a preprocessed face crop.

        Returns a ``Prediction`` if a match exceeds the similarity threshold,
        or ``None`` for unknown / low-confidence faces.
        """
        ...

    def label_info(self, student_id: int) -> Optional[Dict[str, Any]]:
        """Metadata dict for a trained identity (name, roll_number, etc.)."""
        ...
