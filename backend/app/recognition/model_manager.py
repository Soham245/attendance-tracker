"""Versioned model registry on the local filesystem.

Layout (under ``<STORAGE_DIR>/models/``):

    registry.json       — ordered version manifest (newest first)
    candidate/          — staging slot for the next training/enrollment run
    v001/               — oldest retained version
    v002/               — ...
    v003/               — newest / active version
    active/             — legacy slot, auto-migrated on first access
    backup/             — legacy slot, auto-migrated on first access

On first access after upgrading from the old active/backup layout, the
migration logic promotes existing artifacts into ``v001`` (backup) and
``v002`` (active), writes an initial ``registry.json``, and removes the
legacy directories. This is idempotent — calling it again is a no-op.

Version IDs are monotonically increasing zero-padded integers (``v001``,
``v002``, …). The active version is tracked in ``registry.json`` — no
filesystem symlinks, keeping Windows compatibility.

Retention is configurable via ``MODEL_MAX_RETAINED_VERSIONS``. On each
promotion the oldest versions beyond the limit are pruned from disk and
removed from the manifest.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.core.logging import get_logger
from app.storage.local import (
    ACTIVE_DIR,
    BACKUP_DIR,
    CANDIDATE_DIR,
    LABELS_FILENAME,
    METADATA_FILENAME,
    REGISTRY_FILENAME,
    TRAINER_FILENAME,
    ensure_model_dir,
    model_dir,
    models_root,
    reset_model_dir,
)


logger = get_logger("attendai.model_manager")


# ---------------------------------------------------------------------------
# Registry data model
# ---------------------------------------------------------------------------

@dataclass
class ModelVersion:
    """One entry in the version manifest."""

    id: str                              # e.g. "v003"
    backend: str = "lbph"                # recognition backend that produced it
    created_at: str = ""                 # ISO 8601
    student_count: int = 0
    image_count: int = 0
    status: str = "standby"              # "active" | "standby"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Registry:
    """Persisted model version manifest."""

    active_version: Optional[str] = None
    versions: List[ModelVersion] = field(default_factory=list)
    max_retained: int = 3

    # -- serialization --------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_version": self.active_version,
            "max_retained": self.max_retained,
            "versions": [v.to_dict() for v in self.versions],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Registry":
        versions = [
            ModelVersion(**v) for v in d.get("versions", [])
        ]
        return cls(
            active_version=d.get("active_version"),
            versions=versions,
            max_retained=d.get("max_retained", 3),
        )

    # -- helpers --------------------------------------------------------------

    def active(self) -> Optional[ModelVersion]:
        if self.active_version is None:
            return None
        return next((v for v in self.versions if v.id == self.active_version), None)

    def next_version_id(self) -> str:
        """Return the next version id (e.g. ``v004`` after ``v003``)."""
        if not self.versions:
            return "v001"
        nums = []
        for v in self.versions:
            try:
                nums.append(int(v.id.lstrip("v")))
            except ValueError:
                continue
        return f"v{(max(nums) + 1) if nums else 1:03d}"

    def standby_versions(self) -> List[ModelVersion]:
        """Non-active versions, oldest first."""
        return [v for v in self.versions if v.id != self.active_version]


# ---------------------------------------------------------------------------
# Registry I/O
# ---------------------------------------------------------------------------

def _registry_path() -> Path:
    return models_root() / REGISTRY_FILENAME


def _read_registry() -> Registry:
    path = _registry_path()
    if not path.is_file():
        return Registry(max_retained=settings.MODEL_MAX_RETAINED_VERSIONS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        reg = Registry.from_dict(data)
        reg.max_retained = settings.MODEL_MAX_RETAINED_VERSIONS
        return reg
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to read registry, starting fresh: %s", exc)
        return Registry(max_retained=settings.MODEL_MAX_RETAINED_VERSIONS)


def _write_registry(reg: Registry) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg.to_dict(), indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Legacy migration
# ---------------------------------------------------------------------------

def _maybe_migrate_legacy() -> None:
    """One-time migration from active/backup/ to versioned layout.

    Idempotent: skips entirely if ``registry.json`` already exists or if
    neither ``active/`` nor ``backup/`` contain a model.
    """
    if _registry_path().is_file():
        return  # already migrated

    old_active = model_dir(ACTIVE_DIR)
    old_backup = model_dir(BACKUP_DIR)
    has_active = (old_active / TRAINER_FILENAME).is_file()
    has_backup = (old_backup / TRAINER_FILENAME).is_file()

    if not has_active and not has_backup:
        return  # nothing to migrate

    reg = Registry(max_retained=settings.MODEL_MAX_RETAINED_VERSIONS)
    root = models_root()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Migrate backup/ → v001 (if it exists)
    if has_backup:
        dest = root / "v001"
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        shutil.move(str(old_backup), str(dest))
        meta = _read_json(dest / METADATA_FILENAME)
        reg.versions.append(ModelVersion(
            id="v001",
            backend="lbph",
            created_at=meta.get("trained_at", now_iso) if meta else now_iso,
            student_count=meta.get("student_count", 0) if meta else 0,
            image_count=meta.get("image_count", 0) if meta else 0,
            status="standby",
        ))
        logger.info("Migrated legacy backup/ → v001")

    # Migrate active/ → v002 (or v001 if no backup)
    if has_active:
        vid = "v002" if has_backup else "v001"
        dest = root / vid
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        shutil.move(str(old_active), str(dest))
        meta = _read_json(dest / METADATA_FILENAME)
        reg.versions.append(ModelVersion(
            id=vid,
            backend="lbph",
            created_at=meta.get("trained_at", now_iso) if meta else now_iso,
            student_count=meta.get("student_count", 0) if meta else 0,
            image_count=meta.get("image_count", 0) if meta else 0,
            status="active",
        ))
        reg.active_version = vid
        logger.info("Migrated legacy active/ → %s", vid)

    _write_registry(reg)
    logger.info("Legacy model migration complete (versions=%d)", len(reg.versions))

    # Clean up empty legacy dirs that may remain.
    for d in (old_active, old_backup):
        if d.exists() and not any(d.iterdir()):
            shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# Public API — preserves the interface callers already depend on
# ---------------------------------------------------------------------------

def has_active_model() -> bool:
    """True if an active model version exists on disk with a trainer file."""
    _maybe_migrate_legacy()
    reg = _read_registry()
    if reg.active_version is None:
        return False
    return (models_root() / reg.active_version / TRAINER_FILENAME).is_file()


def active_dir() -> Path:
    """Return the path to the active model version directory.

    Callers use this to load ``trainer.yml``, ``labels.json``, etc.
    Falls back to the legacy ``active/`` path if registry is missing
    (shouldn't happen after migration, but defensive).
    """
    _maybe_migrate_legacy()
    reg = _read_registry()
    if reg.active_version:
        return models_root() / reg.active_version
    # Fallback for truly empty state — return the old path so callers get
    # a clean FileNotFoundError rather than a confusing None-path.
    return model_dir(ACTIVE_DIR)


def candidate_dir() -> Path:
    return model_dir(CANDIDATE_DIR)


def backup_dir() -> Path:
    """Deprecated. Kept for any stray callers during migration period."""
    return model_dir(BACKUP_DIR)


def prepare_candidate() -> Path:
    """Wipe and recreate candidate/ so training writes into a clean slot."""
    return reset_model_dir(CANDIDATE_DIR)


def write_artifacts(
    folder: Path,
    *,
    labels: Dict[int, Dict[str, Any]],
    metadata: Dict[str, Any],
) -> None:
    """Write labels.json + metadata.json. trainer.yml is written by OpenCV."""
    (folder / LABELS_FILENAME).write_text(
        json.dumps(labels, indent=2), encoding="utf-8"
    )
    (folder / METADATA_FILENAME).write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )


def promote_candidate() -> str:
    """Promote candidate/ to a new versioned model directory.

    Returns the new version ID (e.g. ``"v003"``).

    Sequence:
      1. Read or create registry.
      2. Assign next version ID.
      3. Move candidate/ → v{NNN}/.
      4. Mark new version as active, old active as standby.
      5. Prune oldest versions beyond retention limit.
      6. Write updated registry.
    """
    _maybe_migrate_legacy()

    cand = candidate_dir()
    if not (cand / TRAINER_FILENAME).is_file():
        raise FileNotFoundError("No candidate model to promote")

    reg = _read_registry()
    new_id = reg.next_version_id()
    dest = models_root() / new_id

    # Move candidate → versioned dir.
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    shutil.move(str(cand), str(dest))

    # Read metadata from the newly moved version for registry entry.
    meta = _read_json(dest / METADATA_FILENAME)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Demote current active to standby.
    for v in reg.versions:
        if v.status == "active":
            v.status = "standby"

    reg.versions.append(ModelVersion(
        id=new_id,
        backend=settings.RECOGNITION_BACKEND,
        created_at=meta.get("trained_at", now_iso) if meta else now_iso,
        student_count=meta.get("student_count", 0) if meta else 0,
        image_count=meta.get("image_count", 0) if meta else 0,
        status="active",
    ))
    reg.active_version = new_id

    # Prune: keep at most max_retained versions.
    _prune(reg)

    _write_registry(reg)
    logger.info("Promoted candidate model to %s", new_id)
    return new_id


def rollback(version_id: str) -> None:
    """Set a standby version as active.

    Raises ValueError if the version doesn't exist or is already active.
    Raises FileNotFoundError if the version directory is missing on disk.
    """
    _maybe_migrate_legacy()
    reg = _read_registry()

    target = next((v for v in reg.versions if v.id == version_id), None)
    if target is None:
        raise ValueError(f"Version {version_id!r} not found in registry")
    if target.id == reg.active_version:
        raise ValueError(f"Version {version_id!r} is already active")

    target_dir = models_root() / version_id
    if not (target_dir / TRAINER_FILENAME).is_file():
        raise FileNotFoundError(
            f"Version {version_id!r} directory missing or incomplete on disk"
        )

    # Swap statuses.
    for v in reg.versions:
        if v.status == "active":
            v.status = "standby"
    target.status = "active"
    reg.active_version = version_id

    _write_registry(reg)
    logger.info("Rolled back to model version %s", version_id)


def list_versions() -> List[Dict[str, Any]]:
    """Return all retained model versions (newest first)."""
    _maybe_migrate_legacy()
    reg = _read_registry()
    return [v.to_dict() for v in reversed(reg.versions)]


def get_active_metadata() -> Optional[Dict[str, Any]]:
    _maybe_migrate_legacy()
    reg = _read_registry()
    if reg.active_version is None:
        return None
    meta = _read_json(models_root() / reg.active_version / METADATA_FILENAME)
    if meta is None:
        return None
    # Enrich with registry info.
    meta["version"] = reg.active_version
    meta["backend"] = settings.RECOGNITION_BACKEND
    meta["available_versions"] = len(reg.versions)
    return meta


def delete_version(version_id: str) -> None:
    """Delete a single non-active model version from disk and registry.

    Raises ValueError if the version is currently active or not found.
    """
    _maybe_migrate_legacy()
    reg = _read_registry()

    target = next((v for v in reg.versions if v.id == version_id), None)
    if target is None:
        raise ValueError(f"Version {version_id!r} not found in registry")
    if target.id == reg.active_version:
        raise ValueError(f"Cannot delete the active version ({version_id!r})")

    # Remove from disk.
    disk_path = models_root() / version_id
    if disk_path.exists():
        shutil.rmtree(disk_path, ignore_errors=True)

    reg.versions = [v for v in reg.versions if v.id != version_id]
    _write_registry(reg)
    logger.info("Deleted model version %s", version_id)


def drop_all_models() -> int:
    """Delete ALL model versions (including active) and reset the registry.

    Returns the number of versions that were removed. After this call,
    ``has_active_model()`` returns False and ``next_version_id()`` starts
    from ``v001`` again.
    """
    _maybe_migrate_legacy()
    reg = _read_registry()
    count = len(reg.versions)

    # Remove every version directory from disk.
    root = models_root()
    for v in reg.versions:
        disk_path = root / v.id
        if disk_path.exists():
            shutil.rmtree(disk_path, ignore_errors=True)
            logger.info("Removed model version %s from disk", v.id)

    # Also remove candidate/ if it exists.
    cand = root / CANDIDATE_DIR
    if cand.exists():
        shutil.rmtree(cand, ignore_errors=True)

    # Write a blank registry.
    fresh = Registry(max_retained=settings.MODEL_MAX_RETAINED_VERSIONS)
    _write_registry(fresh)
    logger.info("Dropped all %d model versions; registry reset", count)
    return count


def get_active_labels() -> Optional[Dict[str, Any]]:
    _maybe_migrate_legacy()
    reg = _read_registry()
    if reg.active_version is None:
        return None
    return _read_json(models_root() / reg.active_version / LABELS_FILENAME)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return None


def _prune(reg: Registry) -> None:
    """Remove oldest versions beyond the retention limit from disk + registry."""
    while len(reg.versions) > reg.max_retained:
        oldest = reg.versions[0]
        if oldest.id == reg.active_version:
            # Safety: never prune the active version even if it's the oldest.
            # This shouldn't happen with normal flow, but be defensive.
            break
        disk_path = models_root() / oldest.id
        if disk_path.exists():
            shutil.rmtree(disk_path, ignore_errors=True)
            logger.info("Pruned model version %s", oldest.id)
        reg.versions.pop(0)
