"""Dataset capture pipeline: frame -> processed face sample.

Single responsibility: take a BGR webcam frame, return a normalized grayscale
face crop suitable for LBPH training, or `None` if no usable face is present.

No I/O, no model loading, no recognition. The capture runtime owns the
camera + dataset writes; this file owns the visual pipeline only.

Pipeline:
    frame (BGR)
      -> grayscale conversion
      -> Haar cascade face detection
      -> largest face selection
      -> minimum size filter
      -> crop face region
      -> resize to CAPTURE_FACE_SIZE (square)
      -> encode as JPEG bytes
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from app.config.settings import settings
from app.recognition.preprocess import prepare_face


# (x, y, w, h) — same convention as the recognition detector.
BoundingBox = Tuple[int, int, int, int]


@dataclass
class CapturePipeline:
    """Encapsulates the cascade + tunables for capture face extraction.

    Kept distinct from `recognition.detector.FaceDetector` because capture
    has different acceptance rules (largest face, minimum size, no scoring)
    and may diverge further as the runtime evolves.
    """

    cascade: Any
    scale_factor: float
    min_neighbors: int
    face_size: int
    min_face_fraction: float

    @classmethod
    def load(cls) -> "CapturePipeline":
        import cv2  # noqa: PLC0415 — lazy so backend boots without OpenCV

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            raise RuntimeError(f"Failed to load Haar cascade at {cascade_path}")
        return cls(
            cascade=cascade,
            scale_factor=settings.CAPTURE_DETECT_SCALE_FACTOR,
            min_neighbors=settings.CAPTURE_DETECT_MIN_NEIGHBORS,
            face_size=settings.CAPTURE_FACE_SIZE,
            min_face_fraction=settings.CAPTURE_DETECT_MIN_FACE_FRACTION,
        )

    def extract_sample(self, frame_bgr: Any) -> Optional[bytes]:
        """Return JPEG bytes of the largest acceptable face, or None.

        Accepts a frame from `cv2.VideoCapture.read()`. Returns None when:
            - no face is detected, or
            - the largest face is smaller than the configured minimum.
        """
        import cv2  # noqa: PLC0415

        if frame_bgr is None:
            return None

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        face = self._select_face(gray)
        if face is None:
            return None

        x, y, w, h = face
        crop = gray[y : y + h, x : x + w]
        normalized = cv2.resize(
            crop,
            (self.face_size, self.face_size),
            interpolation=cv2.INTER_AREA,
        )
        normalized = prepare_face(normalized)

        ok, buf = cv2.imencode(".jpg", normalized)
        if not ok:
            return None
        return buf.tobytes()

    # -- internals --

    def _select_face(self, gray_frame: Any) -> Optional[BoundingBox]:
        """Return the largest detected face that meets the size threshold."""
        rects = self.cascade.detectMultiScale(
            gray_frame,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
        )
        if len(rects) == 0:
            return None

        # Choose the largest detection — capture is a single-subject flow,
        # so any background face is noise.
        x, y, w, h = max(rects, key=lambda r: int(r[2]) * int(r[3]))
        frame_h, frame_w = gray_frame.shape[:2]
        min_side = self.min_face_fraction * min(frame_h, frame_w)
        if min(w, h) < min_side:
            return None
        return int(x), int(y), int(w), int(h)
