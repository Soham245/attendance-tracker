"""YuNet face detector backend via OpenCV's FaceDetectorYN.

YuNet is a lightweight DNN face detector that ships as a ~340 KB ONNX
model. OpenCV 4.5.4+ includes ``cv2.FaceDetectorYN`` which handles all
pre/post-processing internally — no ``onnxruntime`` dependency needed.

Advantages over Haar cascades:
  - Higher detection accuracy (especially at angles and low light).
  - Produces 5-point facial landmarks (eyes, nose, mouth corners) —
    required for ArcFace alignment in Phase 3.
  - Native confidence score per detection.

The ONNX model file is auto-downloaded on first use via
``model_downloader.ensure_yunet_model()``.

Output format from ``cv2.FaceDetectorYN.detect()``:
    Each row is 15 floats:
    [x, y, w, h,
     right_eye_x, right_eye_y,
     left_eye_x, left_eye_y,
     nose_x, nose_y,
     right_mouth_x, right_mouth_y,
     left_mouth_x, left_mouth_y,
     score]
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from app.config.settings import settings
from app.recognition.detectors.base import (
    BoundingBox,
    DetectionResult,
    FaceDetectorBackend,
)
from app.recognition.detectors.model_downloader import ensure_yunet_model


class YuNetDetectorBackend:
    """YuNet face detection via ``cv2.FaceDetectorYN``."""

    def __init__(
        self,
        detector: Any,  # cv2.FaceDetectorYN instance
    ) -> None:
        self._det = detector

    @classmethod
    def load(cls) -> "YuNetDetectorBackend":
        import cv2  # noqa: PLC0415

        model_path = ensure_yunet_model()
        input_size = settings.YUNET_INPUT_SIZE

        detector = cv2.FaceDetectorYN.create(
            model=str(model_path),
            config="",
            input_size=(input_size, input_size),
            score_threshold=settings.YUNET_SCORE_THRESHOLD,
            nms_threshold=settings.YUNET_NMS_THRESHOLD,
            top_k=5000,
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
            target_id=cv2.dnn.DNN_TARGET_CPU,
        )
        return cls(detector=detector)

    # -- FaceDetectorBackend interface ----------------------------------------

    @property
    def backend_name(self) -> str:
        return "yunet"

    def detect(self, gray_frame: Any) -> List[DetectionResult]:
        import cv2  # noqa: PLC0415

        # FaceDetectorYN expects a 3-channel image. If grayscale, convert.
        if len(gray_frame.shape) == 2:
            img = cv2.cvtColor(gray_frame, cv2.COLOR_GRAY2BGR)
        else:
            img = gray_frame

        h, w = img.shape[:2]
        # Update input size to match current frame dimensions.
        self._det.setInputSize((w, h))

        retval, faces = self._det.detect(img)
        if faces is None:
            return []

        results: List[DetectionResult] = []
        for face in faces:
            det = self._parse_face(face, frame_w=w, frame_h=h)
            if det is not None:
                results.append(det)
        return results

    def detect_largest(self, gray_frame: Any) -> Optional[DetectionResult]:
        dets = self.detect(gray_frame)
        if not dets:
            return None
        return max(dets, key=lambda d: d.bbox[2] * d.bbox[3])

    # -- internals ------------------------------------------------------------

    @staticmethod
    def _parse_face(
        row: Any, frame_w: int, frame_h: int
    ) -> Optional[DetectionResult]:
        """Parse one row from FaceDetectorYN output into a DetectionResult."""
        # row: [x, y, w, h, re_x, re_y, le_x, le_y, n_x, n_y, rm_x, rm_y, lm_x, lm_y, score]
        x = max(0, int(row[0]))
        y = max(0, int(row[1]))
        w = int(row[2])
        h = int(row[3])

        # Clamp to frame bounds.
        if x + w > frame_w:
            w = frame_w - x
        if y + h > frame_h:
            h = frame_h - y
        if w <= 0 or h <= 0:
            return None

        bbox: BoundingBox = (x, y, w, h)
        score = float(row[14])

        # 5-point landmarks: right eye, left eye, nose, right mouth, left mouth.
        landmarks: List[Tuple[int, int]] = [
            (int(row[4]), int(row[5])),    # right eye
            (int(row[6]), int(row[7])),    # left eye
            (int(row[8]), int(row[9])),    # nose tip
            (int(row[10]), int(row[11])),  # right mouth corner
            (int(row[12]), int(row[13])),  # left mouth corner
        ]

        return DetectionResult(
            bbox=bbox,
            confidence=round(score, 4),
            landmarks=landmarks,
        )


# Type assertion.
assert isinstance(
    YuNetDetectorBackend.__new__(YuNetDetectorBackend), FaceDetectorBackend
)
