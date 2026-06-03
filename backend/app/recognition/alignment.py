"""Face alignment for ArcFace embedding extraction.

Aligns a face crop to the canonical 112x112 position expected by ArcFace
models using a similarity transform derived from 5-point facial landmarks.

The reference landmarks define where eyes, nose, and mouth corners should
sit in the output image. They come from the insightface/ArcFace training
pipeline and must be used as-is for the embeddings to be meaningful.

Requires a detection backend that produces landmarks (e.g. YuNet). If
landmarks are not available the fallback is a simple center-crop + resize,
which works but produces lower-quality embeddings.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np


# Canonical 5-point landmark positions in the 112x112 output space.
# Order: left eye, right eye, nose tip, left mouth corner, right mouth corner.
# Source: insightface/utils/face_align.py — must match training preprocessing.
ARCFACE_REFERENCE_LANDMARKS = np.array(
    [
        [38.2946, 51.6963],   # left eye
        [73.5318, 51.5014],   # right eye
        [56.0252, 71.7366],   # nose tip
        [41.5493, 92.3655],   # left mouth corner
        [70.7299, 92.2041],   # right mouth corner
    ],
    dtype=np.float32,
)


def align_face(
    img_bgr: np.ndarray,
    landmarks: List[Tuple[int, int]],
    output_size: int = 112,
) -> np.ndarray:
    """Warp *img_bgr* so the face lands in canonical ArcFace position.

    Parameters
    ----------
    img_bgr : (H, W, 3) uint8
        Full-frame BGR image from the camera.
    landmarks : list of 5 (x, y) tuples
        Detected 5-point landmarks in *img_bgr* coordinates.
        Order: right eye, left eye, nose, right mouth, left mouth
        (YuNet order — note right/left refer to the subject's perspective
        in YuNet output, which we remap to match ArcFace reference).
    output_size : int
        Side length of the square output image (default 112).

    Returns
    -------
    aligned : (112, 112, 3) uint8 BGR image
    """
    import cv2  # noqa: PLC0415

    # YuNet landmark order:  right_eye, left_eye, nose, right_mouth, left_mouth
    # ArcFace reference:     left_eye,  right_eye, nose, left_mouth, right_mouth
    # Remap YuNet → ArcFace order.
    src_pts = np.array(
        [
            landmarks[1],  # left eye  (YuNet index 1)
            landmarks[0],  # right eye (YuNet index 0)
            landmarks[2],  # nose      (YuNet index 2)
            landmarks[4],  # left mouth  (YuNet index 4)
            landmarks[3],  # right mouth (YuNet index 3)
        ],
        dtype=np.float32,
    )

    dst_pts = ARCFACE_REFERENCE_LANDMARKS.copy()
    if output_size != 112:
        scale = output_size / 112.0
        dst_pts *= scale

    # Estimate similarity transform (rotation + uniform scale + translation).
    # estimateAffinePartial2D is the OpenCV equivalent of skimage's
    # SimilarityTransform.estimate — 4 DOF, robust to outliers.
    M, _inliers = cv2.estimateAffinePartial2D(
        src_pts, dst_pts, method=cv2.LMEDS
    )

    if M is None:
        # Fallback: simple center-crop resize if transform estimation fails.
        return _fallback_crop(img_bgr, landmarks, output_size)

    aligned = cv2.warpAffine(
        img_bgr, M, (output_size, output_size), borderValue=(0, 0, 0)
    )
    return aligned


def align_face_from_bbox(
    img_bgr: np.ndarray,
    bbox: Tuple[int, int, int, int],
    output_size: int = 112,
) -> np.ndarray:
    """Fallback alignment: crop bbox region and resize.

    Used when the detector doesn't produce landmarks (e.g. Haar cascade).
    Lower quality than landmark-based alignment but still functional.
    """
    import cv2  # noqa: PLC0415

    x, y, w, h = bbox
    h_img, w_img = img_bgr.shape[:2]

    # Expand bbox to square (center-anchored).
    side = max(w, h)
    cx, cy = x + w // 2, y + h // 2
    x1 = max(0, cx - side // 2)
    y1 = max(0, cy - side // 2)
    x2 = min(w_img, x1 + side)
    y2 = min(h_img, y1 + side)

    crop = img_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return np.zeros((output_size, output_size, 3), dtype=np.uint8)

    return cv2.resize(crop, (output_size, output_size), interpolation=cv2.INTER_LINEAR)


def _fallback_crop(
    img_bgr: np.ndarray,
    landmarks: List[Tuple[int, int]],
    output_size: int,
) -> np.ndarray:
    """Derive a bounding box from landmarks and do a simple crop+resize."""
    pts = np.array(landmarks, dtype=np.float32)
    x_min, y_min = pts.min(axis=0)
    x_max, y_max = pts.max(axis=0)
    # Expand by 50% of the landmark span for a generous face box.
    pad_x = (x_max - x_min) * 0.5
    pad_y = (y_max - y_min) * 0.5
    bbox = (
        int(x_min - pad_x),
        int(y_min - pad_y),
        int(x_max - x_min + 2 * pad_x),
        int(y_max - y_min + 2 * pad_y),
    )
    return align_face_from_bbox(img_bgr, bbox, output_size)
