"""ArcFace embedding recognition backend.

Runs a pretrained ArcFace model (ONNX Runtime) to extract 512-d face
embeddings, then matches against an enrolled gallery via cosine similarity.

The ArcFace model is a **frozen, pretrained network** — it is never
fine-tuned or retrained. "Enrollment" means running forward passes on
each student's dataset images to build a gallery of reference embeddings.
At runtime, each detected face is embedded and compared to the gallery.

Input preprocessing (must match training):
  - 112x112 BGR image (aligned via 5-point landmarks)
  - Convert BGR → RGB
  - Normalise: pixel / 127.5 - 1.0  →  range [-1, 1]
  - Transpose to NCHW: (1, 3, 112, 112)

Output:
  - 512-d float32 vector, L2-normalized
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from app.config.settings import settings
from app.core.logging import get_logger
from app.recognition.backends.base import Prediction, RecognizerBackend
from app.recognition.detectors.model_downloader import ensure_arcface_model
from app.recognition.gallery import EmbeddingGallery


logger = get_logger("attendai.arcface")

GALLERY_FILENAME = "gallery.npz"


class ArcFaceBackend:
    """Embedding-based recognition via ArcFace ONNX + gallery cosine search."""

    def __init__(
        self,
        session: Any,  # onnxruntime.InferenceSession
        gallery: EmbeddingGallery,
        labels: Dict[str, Dict[str, Any]],
        threshold: float,
        input_name: str,
    ) -> None:
        self._session = session
        self._gallery = gallery
        self._labels = labels
        self._threshold = threshold
        self._input_name = input_name

    @classmethod
    def load_active(cls) -> "ArcFaceBackend":
        """Construct from the active model version's gallery + ONNX model."""
        import onnxruntime as ort  # noqa: PLC0415

        from app.recognition import model_manager

        # Load the ONNX model (shared, not per-version).
        model_path = ensure_arcface_model()
        session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )
        input_name = session.get_inputs()[0].name

        # Load per-version gallery + labels from the active model dir.
        active = model_manager.active_dir()
        gallery_path = active / GALLERY_FILENAME
        if not gallery_path.is_file():
            raise FileNotFoundError(
                f"No embedding gallery at {gallery_path}. "
                f"Run enrollment with RECOGNITION_BACKEND=arcface first."
            )
        gallery = EmbeddingGallery.load(gallery_path)

        labels_data = model_manager.get_active_labels() or {}

        return cls(
            session=session,
            gallery=gallery,
            labels=labels_data,
            threshold=settings.ARCFACE_SIMILARITY_THRESHOLD,
            input_name=input_name,
        )

    # -- RecognizerBackend interface ------------------------------------------

    @property
    def backend_name(self) -> str:
        return "arcface"

    @property
    def similarity_threshold(self) -> float:
        return self._threshold

    def predict(self, face_crop: Any) -> Optional[Prediction]:
        """Extract embedding from face crop and search gallery.

        Parameters
        ----------
        face_crop : np.ndarray
            112x112 BGR image (aligned). If grayscale, it's converted to BGR.
            The pipeline is responsible for alignment before calling this.
        """
        embedding = self.extract_embedding(face_crop)
        match = self._gallery.search_with_aggregation(embedding)
        if match is None or match.similarity < self._threshold:
            return None

        return Prediction(
            student_id=match.student_id,
            similarity=round(float(match.similarity), 4),
            raw_metric=round(float(match.similarity), 4),
            backend="arcface",
        )

    def label_info(self, student_id: int) -> Optional[Dict[str, Any]]:
        return self._labels.get(str(student_id))

    # -- embedding extraction (also used by enrollment) -----------------------

    def extract_embedding(self, face_bgr: np.ndarray) -> np.ndarray:
        """Run ArcFace forward pass → L2-normalised 512-d embedding.

        Parameters
        ----------
        face_bgr : (112, 112, 3) uint8 BGR or (112, 112) grayscale

        Returns
        -------
        embedding : (512,) float32, L2-normalised
        """
        import cv2  # noqa: PLC0415

        if face_bgr.ndim == 2:
            face_bgr = cv2.cvtColor(face_bgr, cv2.COLOR_GRAY2BGR)

        # Resize to 112x112 if needed.
        if face_bgr.shape[:2] != (112, 112):
            face_bgr = cv2.resize(face_bgr, (112, 112))

        # BGR → RGB → float → normalise to [-1, 1].
        rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)
        rgb = (rgb / 127.5) - 1.0

        # HWC → NCHW.
        blob = np.transpose(rgb, (2, 0, 1))[np.newaxis, ...]

        # Forward pass.
        outputs = self._session.run(None, {self._input_name: blob})
        embedding = outputs[0].flatten().astype(np.float32)

        # L2 normalise.
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding
