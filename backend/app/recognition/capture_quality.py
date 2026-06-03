"""Face quality evaluation for guided biometric enrollment.

OpenCV heuristics only — no landmarks, no deep learning.  Evaluates:
  - face size relative to frame
  - face centeredness
  - detection stability (bbox jitter across consecutive frames)
  - sharpness (variance of Laplacian — rejects blurry captures)
  - brightness (grayscale mean — rejects under/over-exposed captures)
  - pose shift (face-center-x delta between phases)

Returns a lightweight QualityResult the capture runtime uses to gate
sample persistence and drive overlay annotations.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

from app.config.settings import settings


@dataclass
class QualityResult:
    face_detected: bool = False
    bbox: Optional[Tuple[int, int, int, int]] = None
    acceptable: bool = False
    face_ratio: float = 0.0
    center_offset: float = 1.0
    stable: bool = False
    sharp: bool = True
    sharpness: float = 0.0
    brightness_ok: bool = True
    brightness_level: str = "ok"  # "ok" | "dark" | "bright"
    brightness_mean: float = 128.0
    pose_shift_ok: bool = True
    guidance: str = "Position your face in the frame"


# Enrollment phases — the runtime cycles through these.
PHASES = [
    {"id": "front",       "instruction": "Look straight ahead"},
    {"id": "right",       "instruction": "Slowly turn right"},
    {"id": "left",        "instruction": "Slowly turn left"},
    {"id": "front_again", "instruction": "Look forward again"},
]


class QualityEvaluator:
    """Stateful evaluator — tracks bbox history for stability checks."""

    def __init__(self) -> None:
        self._history: deque[Tuple[int, int, int, int]] = deque(
            maxlen=settings.CAPTURE_QUALITY_STABILITY_FRAMES
        )
        # Pose tracking: face center-x at the start of each phase.
        self._phase_anchor_cx: Optional[float] = None

    def evaluate(
        self,
        bbox: Optional[Tuple[int, int, int, int]],
        frame_h: int,
        frame_w: int,
        *,
        gray_crop: Any = None,
    ) -> QualityResult:
        if bbox is None:
            self._history.clear()
            return QualityResult(guidance="No face detected — look at the camera")

        x, y, w, h = bbox
        frame_area = frame_h * frame_w
        face_area = w * h

        face_ratio = face_area / frame_area if frame_area > 0 else 0.0

        face_cx = x + w / 2
        face_cy = y + h / 2
        frame_cx = frame_w / 2
        frame_cy = frame_h / 2
        dx = abs(face_cx - frame_cx) / frame_cx if frame_cx > 0 else 1.0
        dy = abs(face_cy - frame_cy) / frame_cy if frame_cy > 0 else 1.0
        center_offset = math.sqrt(dx * dx + dy * dy) / math.sqrt(2)

        self._history.append(bbox)
        stable = self._is_stable()

        # Image quality checks on the face crop.
        sharp = True
        sharpness = 0.0
        brightness_ok = True
        brightness_level = "ok"
        brightness_mean = 128.0

        if gray_crop is not None:
            sharpness = self._measure_sharpness(gray_crop)
            sharp = sharpness >= settings.CAPTURE_QUALITY_MIN_SHARPNESS

            brightness_mean = float(gray_crop.mean())
            if brightness_mean < settings.CAPTURE_QUALITY_MIN_BRIGHTNESS:
                brightness_ok = False
                brightness_level = "dark"
            elif brightness_mean > settings.CAPTURE_QUALITY_MAX_BRIGHTNESS:
                brightness_ok = False
                brightness_level = "bright"

        # Pose shift check (only relevant after first phase).
        pose_shift_ok = True
        face_cx_norm = face_cx / frame_w if frame_w > 0 else 0.5
        if self._phase_anchor_cx is not None:
            shift = abs(face_cx_norm - self._phase_anchor_cx)
            pose_shift_ok = shift >= settings.CAPTURE_QUALITY_MIN_POSE_SHIFT

        # Build guidance message (priority order)
        if face_ratio < settings.CAPTURE_QUALITY_MIN_FACE_RATIO:
            guidance = "Move closer"
        elif center_offset > settings.CAPTURE_QUALITY_MAX_CENTER_OFFSET:
            guidance = "Center your face"
        elif not sharp:
            guidance = "Hold steady — image blurry"
        elif not brightness_ok:
            if brightness_level == "dark":
                guidance = "Too dark — improve lighting"
            else:
                guidance = "Too bright — reduce lighting"
        elif not pose_shift_ok:
            guidance = "Turn more — insufficient pose change"
        elif not stable:
            guidance = "Hold steady"
        else:
            guidance = "Good — hold still"

        acceptable = (
            face_ratio >= settings.CAPTURE_QUALITY_MIN_FACE_RATIO
            and center_offset <= settings.CAPTURE_QUALITY_MAX_CENTER_OFFSET
            and stable
            and sharp
            and brightness_ok
            and pose_shift_ok
        )

        return QualityResult(
            face_detected=True,
            bbox=bbox,
            acceptable=acceptable,
            face_ratio=round(face_ratio, 4),
            center_offset=round(center_offset, 4),
            stable=stable,
            sharp=sharp,
            sharpness=round(sharpness, 1),
            brightness_ok=brightness_ok,
            brightness_level=brightness_level,
            brightness_mean=round(brightness_mean, 1),
            pose_shift_ok=pose_shift_ok,
            guidance=guidance,
        )

    # -- pose tracking --

    def anchor_phase(self, face_cx_norm: float) -> None:
        """Record the face center-x at the START of a new phase.

        Called by the capture runtime on phase transition. The evaluator then
        requires a minimum shift away from this anchor before accepting
        samples — ensuring the student actually changed pose.
        """
        self._phase_anchor_cx = face_cx_norm

    def clear_pose_anchor(self) -> None:
        self._phase_anchor_cx = None

    # -- internals --

    def _is_stable(self) -> bool:
        if len(self._history) < settings.CAPTURE_QUALITY_STABILITY_FRAMES:
            return False
        thresh = settings.CAPTURE_QUALITY_STABILITY_THRESH
        boxes = list(self._history)
        for i in range(1, len(boxes)):
            px, py, pw, ph = boxes[i - 1]
            cx, cy, cw, ch = boxes[i]
            jitter = math.sqrt((cx - px) ** 2 + (cy - py) ** 2 + (cw - pw) ** 2 + (ch - ph) ** 2)
            if jitter > thresh:
                return False
        return True

    @staticmethod
    def _measure_sharpness(gray_crop: Any) -> float:
        import cv2  # noqa: PLC0415
        return float(cv2.Laplacian(gray_crop, cv2.CV_64F).var())

    def reset(self) -> None:
        self._history.clear()
        self._phase_anchor_cx = None
