"""Filesystem path helpers used by infrastructure (lifespan, storage)."""
from pathlib import Path
from typing import Union


def ensure_dir(path: Union[str, Path]) -> Path:
    """Create `path` (and parents) if missing; return the resolved Path."""
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p
