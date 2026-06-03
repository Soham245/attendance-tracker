"""Shared face preprocessing for enrollment, training, and recognition.

Applies contrast normalization to a grayscale face crop. Two modes:

- **CLAHE** (when `CLAHE_ENABLED=True`): adaptive per-tile, clip-limited
  histogram equalization. Better in theory, but can alter LBPH's local
  texture patterns in ways that reduce discriminability.

- **equalizeHist** (default): global histogram stretch. Simpler but
  well-proven with LBPH on typical webcam feeds.

Using the SAME preprocessing at capture, training, and recognition is
critical — asymmetric normalization degrades LBPH accuracy because the
texture patterns the model learns don't match what it sees at inference.
"""
from __future__ import annotations

from typing import Any

from app.config.settings import settings


def prepare_face(gray_crop: Any) -> Any:
    """Apply contrast normalization to a grayscale face crop."""
    import cv2  # noqa: PLC0415

    if settings.CLAHE_ENABLED:
        clahe = cv2.createCLAHE(
            clipLimit=settings.CLAHE_CLIP_LIMIT,
            tileGridSize=(settings.CLAHE_TILE_SIZE, settings.CLAHE_TILE_SIZE),
        )
        return clahe.apply(gray_crop)

    return cv2.equalizeHist(gray_crop)
