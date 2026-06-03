"""Local filesystem layout for student datasets.

Layout (rooted at `settings.STORAGE_DIR`):
    datasets/<student_id>/<image_filename>

The DB stores `dataset_path` as the relative folder path (`datasets/<id>`),
keeping records portable. The filesystem is the source of truth for image
files — there is no image-metadata table.
"""
from pathlib import Path
from typing import List, Tuple
import shutil

from app.config.settings import settings
from app.utils.paths import ensure_dir


DATASETS_SUBDIR = "datasets"
MODELS_SUBDIR = "models"

# Subfolders inside MODELS_SUBDIR.
ACTIVE_DIR = "active"
CANDIDATE_DIR = "candidate"
BACKUP_DIR = "backup"

# Artifact filenames written inside each model subfolder.
TRAINER_FILENAME = "trainer.yml"
LABELS_FILENAME = "labels.json"
METADATA_FILENAME = "metadata.json"
REGISTRY_FILENAME = "registry.json"
GALLERY_FILENAME = "gallery.npz"


def _storage_root() -> Path:
    return Path(settings.STORAGE_DIR).expanduser().resolve()


def student_dataset_relpath(student_id: int) -> str:
    return f"{DATASETS_SUBDIR}/{student_id}"


def student_dataset_path(student_id: int) -> Path:
    return _storage_root() / DATASETS_SUBDIR / str(student_id)


def ensure_student_dataset(student_id: int) -> Path:
    return ensure_dir(student_dataset_path(student_id))


def remove_student_dataset(student_id: int) -> None:
    path = student_dataset_path(student_id)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def list_student_images(student_id: int) -> List[Tuple[str, int]]:
    """Return [(filename, size_bytes), ...] for files directly in the folder."""
    folder = student_dataset_path(student_id)
    if not folder.is_dir():
        return []
    out: List[Tuple[str, int]] = []
    for entry in sorted(folder.iterdir()):
        if entry.is_file():
            out.append((entry.name, entry.stat().st_size))
    return out


def write_student_image(student_id: int, filename: str, data: bytes) -> Path:
    """Write image bytes to disk; caller is responsible for filename uniqueness."""
    folder = ensure_student_dataset(student_id)
    path = folder / filename
    with path.open("wb") as fh:
        fh.write(data)
    return path


def models_root() -> Path:
    return _storage_root() / MODELS_SUBDIR


def model_dir(slot: str) -> Path:
    return models_root() / slot


def ensure_model_dir(slot: str) -> Path:
    return ensure_dir(model_dir(slot))


def reset_model_dir(slot: str) -> Path:
    """Drop and recreate the slot directory so it starts empty."""
    path = model_dir(slot)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    return ensure_dir(path)


def resolve_student_image(student_id: int, filename: str) -> Path:
    """Resolve `filename` inside the student dataset, rejecting traversal."""
    folder = student_dataset_path(student_id).resolve()
    candidate = (folder / filename).resolve()
    # `candidate` must be a direct child of `folder` — no nested paths, no `..`.
    if candidate.parent != folder:
        raise ValueError("Invalid image path")
    return candidate
