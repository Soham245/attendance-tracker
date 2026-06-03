"""Draw recognition overlays onto a BGR frame for the MJPEG preview.

Pure rendering — no recognition logic, no attendance rules.  Receives
pre-computed detection results and draws boxes + labels + status tags.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


# BGR colours
_GREEN = (0, 200, 100)
_BLUE = (200, 160, 0)
_YELLOW = (0, 210, 255)
_RED = (60, 60, 220)
_GRAY = (120, 120, 120)
_WHITE = (255, 255, 255)


@dataclass
class FaceAnnotation:
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    label: Optional[str] = None      # student name or None
    confidence: Optional[float] = None
    status: str = "unknown"          # "marked" | "already_marked" | "unknown" | "stale" | "out_of_class"


def annotate_frame(
    frame_bgr: Any,
    annotations: List[FaceAnnotation],
) -> Any:
    """Draw overlays in-place and return the same frame (mutated)."""
    import cv2  # noqa: PLC0415

    for ann in annotations:
        x, y, w, h = ann.bbox
        colour, tag = _style_for(ann.status)

        # Bounding box
        cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), colour, 2)

        # Label background + text
        parts = []
        if ann.status == "stale":
            # Stale predictions still show the predicted name so the operator
            # knows which trained label triggered, but explicitly flag it.
            parts.append(f"{ann.label}?" if ann.label else "?")
            parts.append("Not in DB")
        elif ann.status == "out_of_class":
            # Recognised student who is not enrolled in the selected class.
            # Show name so the operator knows who it is, plus a clear warning.
            parts.append(ann.label or "?")
            parts.append("Not in this class")
        else:
            if ann.label:
                parts.append(ann.label)
            if ann.confidence is not None:
                parts.append(f"{ann.confidence:.0%}")
        text = " · ".join(parts) if parts else tag

        _draw_label(frame_bgr, text, x, y - 6, colour)

        # Status tag below the box
        _draw_label(frame_bgr, tag, x, y + h + 16, colour)

    return frame_bgr


_ORANGE = (0, 140, 255)


def _style_for(status: str) -> Tuple[Tuple[int, int, int], str]:
    if status == "marked":
        return _GREEN, "Marked"
    if status == "already_marked":
        return _BLUE, "Already marked"
    if status == "out_of_class":
        return _ORANGE, "Not in this class"
    if status == "stale":
        return _RED, "Retrain required"
    return _YELLOW, "Unknown"


def _draw_label(
    frame: Any, text: str, x: int, y: int, colour: Tuple[int, int, int]
) -> None:
    import cv2  # noqa: PLC0415

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thickness = 1
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    # Background rectangle
    pad = 3
    cv2.rectangle(
        frame,
        (x, y - th - pad),
        (x + tw + pad * 2, y + baseline + pad),
        (0, 0, 0),
        cv2.FILLED,
    )
    cv2.putText(frame, text, (x + pad, y), font, scale, colour, thickness, cv2.LINE_AA)
