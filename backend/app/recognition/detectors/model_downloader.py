"""One-time download of DNN model files for detection + recognition.

Model files are cached in ``<STORAGE_DIR>/onnx_models/``. Downloads use
``urllib`` (stdlib) to avoid adding ``requests`` for a one-shot operation.

Managed models:
  - **YuNet** face detector (~233 KB) — from OpenCV Zoo
  - **ArcFace** embedding model (~12–166 MB) — MobileFaceNet or ResNet50
"""
from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path
from typing import Optional

from app.config.settings import settings
from app.core.logging import get_logger
from app.utils.paths import ensure_dir


logger = get_logger("attendai.model_downloader")


_ONNX_DIR_NAME = "onnx_models"


def _onnx_dir() -> Path:
    return Path(settings.STORAGE_DIR).expanduser().resolve() / _ONNX_DIR_NAME


def _verify_sha256(path: Path, expected: str) -> bool:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest() == expected


def _download(url: str, dest: Path, label: str, min_size: int = 1000) -> Path:
    """Download a file from *url* to *dest*, with integrity checks."""
    logger.info("Downloading %s from %s", label, url)
    try:
        urllib.request.urlretrieve(url, str(dest))
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise RuntimeError(
            f"Failed to download {label} from {url}: {exc}"
        ) from exc

    if not dest.is_file() or dest.stat().st_size < min_size:
        dest.unlink(missing_ok=True)
        raise RuntimeError(
            f"{label} download produced an empty or missing file"
        )
    return dest


# ---------------------------------------------------------------------------
# YuNet face detector
# ---------------------------------------------------------------------------

_YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"
_YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/"
    "models/face_detection_yunet/" + _YUNET_FILENAME
)
_YUNET_SHA256 = (
    "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
)


def ensure_yunet_model() -> Path:
    """Return the path to the YuNet ONNX model, downloading if missing."""
    dest = ensure_dir(_onnx_dir()) / _YUNET_FILENAME

    if dest.is_file() and dest.stat().st_size > 1000:
        return dest

    dest.unlink(missing_ok=True)
    _download(_YUNET_URL, dest, "YuNet model")

    if not _verify_sha256(dest, _YUNET_SHA256):
        logger.warning(
            "YuNet SHA-256 mismatch — may be a newer upstream version. "
            "Proceeding; update _YUNET_SHA256 if this persists."
        )
    logger.info("YuNet model ready at %s", dest)
    return dest


# ---------------------------------------------------------------------------
# ArcFace embedding models
# ---------------------------------------------------------------------------

# Model variants. MobileFaceNet (w600k_mbf) is recommended for CPU-only
# local inference. ResNet50 (w600k_r50) is ~14x larger but slightly more
# accurate. Both take 112x112 RGB input and output 512-d embeddings.
_ARCFACE_MODELS = {
    "w600k_mbf": {
        "filename": "w600k_mbf.onnx",
        "url": (
            "https://github.com/yakhyo/face-reidentification/releases/download/"
            "v0.0.1/w600k_mbf.onnx"
        ),
        "size_hint": "~13 MB",
        "min_size": 5_000_000,
    },
    "w600k_r50": {
        "filename": "w600k_r50.onnx",
        "url": (
            "https://github.com/yakhyo/face-reidentification/releases/download/"
            "v0.0.1/w600k_r50.onnx"
        ),
        "size_hint": "~166 MB",
        "min_size": 50_000_000,
    },
}

# Fallback message shown when auto-download fails.
_MANUAL_INSTRUCTIONS = (
    "Auto-download of the ArcFace model failed. You can manually place the "
    "ONNX file at: {dest}\n\n"
    "To obtain the model:\n"
    "  1. pip install insightface\n"
    "  2. python -c \"from insightface.app import FaceAnalysis; "
    "FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])\"\n"
    "  3. Copy the .onnx file from ~/.insightface/models/buffalo_l/ "
    "to the path above.\n\n"
    "Or download directly from: {url}"
)


def ensure_arcface_model(model_name: Optional[str] = None) -> Path:
    """Return the path to the ArcFace ONNX model, downloading if missing.

    Uses ``settings.ARCFACE_MODEL_NAME`` when *model_name* is not given.
    Raises ``RuntimeError`` with manual-placement instructions on failure.
    """
    name = model_name or settings.ARCFACE_MODEL_NAME
    spec = _ARCFACE_MODELS.get(name)
    if spec is None:
        raise ValueError(
            f"Unknown ArcFace model {name!r}. "
            f"Available: {list(_ARCFACE_MODELS)}"
        )

    dest = ensure_dir(_onnx_dir()) / spec["filename"]

    if dest.is_file() and dest.stat().st_size >= spec["min_size"]:
        return dest

    # Attempt auto-download.
    dest.unlink(missing_ok=True)
    try:
        _download(
            spec["url"], dest,
            f"ArcFace model ({name}, {spec['size_hint']})",
            min_size=spec["min_size"],
        )
    except RuntimeError:
        raise RuntimeError(
            _MANUAL_INSTRUCTIONS.format(dest=dest, url=spec["url"])
        )

    logger.info("ArcFace model ready at %s (%d bytes)", dest, dest.stat().st_size)
    return dest
