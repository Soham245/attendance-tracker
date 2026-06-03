"""Draw capture-phase overlays onto a BGR frame for the MJPEG capture preview.

Renders: face bounding box (quality-colored), guidance text, phase instruction,
progress indicator, center crosshair guide.
"""
from __future__ import annotations

from typing import Any, Optional, Tuple

from app.recognition.capture_quality import QualityResult


_GREEN = (0, 200, 100)
_YELLOW = (0, 210, 255)
_RED = (0, 80, 255)
_WHITE = (255, 255, 255)
_GRAY = (120, 120, 120)


def annotate_capture_frame(
    frame_bgr: Any,
    quality: QualityResult,
    *,
    phase_label: Optional[str] = None,
    phase_index: int = 0,
    phase_count: int = 4,
    samples_in_phase: int = 0,
    samples_per_phase: int = 4,
    total_collected: int = 0,
    total_target: int = 0,
) -> Any:
    """Draw overlays in-place and return the same frame."""
    import cv2  # noqa: PLC0415

    h, w = frame_bgr.shape[:2]

    # Center guide crosshair (always visible).
    cx, cy = w // 2, h // 2
    arm = min(w, h) // 20
    cv2.line(frame_bgr, (cx - arm, cy), (cx + arm, cy), _GRAY, 1)
    cv2.line(frame_bgr, (cx, cy - arm), (cx, cy + arm), _GRAY, 1)

    # Face bounding box — colour encodes quality.
    if quality.face_detected and quality.bbox:
        if quality.acceptable:
            colour = _GREEN
        elif not quality.sharp or not quality.brightness_ok or not quality.pose_shift_ok:
            colour = _RED
        else:
            colour = _YELLOW
        x, y, bw, bh = quality.bbox
        cv2.rectangle(frame_bgr, (x, y), (x + bw, y + bh), colour, 2)

    # Guidance text — top of frame.
    _draw_text_bar(frame_bgr, quality.guidance, 0, w, _guidance_colour(quality))

    # Phase instruction — bottom of frame.
    if phase_label:
        bottom_text = f"Phase {phase_index + 1}/{phase_count}: {phase_label}"
        _draw_text_bar_bottom(frame_bgr, bottom_text, 0, w, h, _WHITE)

    # Progress — top-right corner.
    if total_target > 0:
        progress = f"{total_collected}/{total_target}"
        _draw_progress(frame_bgr, progress, w, samples_in_phase, samples_per_phase)

    return frame_bgr


def _guidance_colour(q: QualityResult) -> Tuple[int, int, int]:
    if not q.face_detected:
        return _RED
    if q.acceptable:
        return _GREEN
    # Blur/brightness/pose failures get the warning (red) treatment so
    # they stand out more than a positioning nudge.
    if not q.sharp or not q.brightness_ok or not q.pose_shift_ok:
        return _RED
    return _YELLOW


def _draw_text_bar(
    frame: Any, text: str, x: int, frame_w: int, colour: Tuple[int, int, int],
) -> None:
    import cv2  # noqa: PLC0415

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.6
    thickness = 1
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    tx = (frame_w - tw) // 2
    ty = th + 12
    pad = 6
    cv2.rectangle(frame, (tx - pad, ty - th - pad), (tx + tw + pad, ty + baseline + pad), (0, 0, 0), cv2.FILLED)
    cv2.putText(frame, text, (tx, ty), font, scale, colour, thickness, cv2.LINE_AA)


def _draw_text_bar_bottom(
    frame: Any, text: str, x: int, frame_w: int, frame_h: int, colour: Tuple[int, int, int],
) -> None:
    import cv2  # noqa: PLC0415

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thickness = 1
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    tx = (frame_w - tw) // 2
    ty = frame_h - 12
    pad = 4
    cv2.rectangle(frame, (tx - pad, ty - th - pad), (tx + tw + pad, ty + baseline + pad), (0, 0, 0), cv2.FILLED)
    cv2.putText(frame, text, (tx, ty), font, scale, colour, thickness, cv2.LINE_AA)


def _draw_progress(
    frame: Any, text: str, frame_w: int, phase_samples: int, phase_target: int,
) -> None:
    import cv2  # noqa: PLC0415

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thickness = 1
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    tx = frame_w - tw - 14
    ty = th + 12
    pad = 4
    cv2.rectangle(frame, (tx - pad, ty - th - pad), (tx + tw + pad, ty + baseline + pad), (0, 0, 0), cv2.FILLED)
    cv2.putText(frame, text, (tx, ty), font, scale, _WHITE, thickness, cv2.LINE_AA)

    # Phase micro-progress dots below the counter.
    dot_y = ty + baseline + pad + 8
    dot_start_x = tx
    for i in range(phase_target):
        dot_x = dot_start_x + i * 12
        color = _GREEN if i < phase_samples else _GRAY
        cv2.circle(frame, (dot_x + 4, dot_y), 3, color, cv2.FILLED)
