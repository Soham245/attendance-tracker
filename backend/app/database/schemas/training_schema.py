"""Pydantic schemas for training control + status."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class TrainingStatus(BaseModel):
    state: str  # idle | running | completed | failed
    last_run_at: Optional[datetime] = None
    last_error: Optional[str] = None
    student_count: int = 0
    image_count: int = 0
    skipped_images: int = 0
    version: Optional[str] = None  # version ID produced by last run


class ModelMetadata(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    trained_at: datetime
    student_count: int
    image_count: int
    student_ids: List[int]
    labels: Optional[Dict[str, Any]] = None
    # Registry-enriched fields (present when registry is initialized).
    version: Optional[str] = None
    backend: Optional[str] = None
    available_versions: Optional[int] = None


class ModelVersionEntry(BaseModel):
    """One entry in the model version list."""
    id: str
    backend: str = "lbph"
    created_at: Optional[str] = None
    student_count: int = 0
    image_count: int = 0
    status: str = "standby"  # "active" | "standby"


class ModelVersionList(BaseModel):
    """Response for the versions endpoint."""
    versions: List[ModelVersionEntry] = []
    active_version: Optional[str] = None
