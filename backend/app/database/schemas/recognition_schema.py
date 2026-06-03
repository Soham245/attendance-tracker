"""Pydantic schemas for the recognition runtime."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RecognitionEventOut(BaseModel):
    student_id: int
    confidence: float
    recognized_at: datetime
    student_name: Optional[str] = None
    student_code: Optional[str] = None


class RecognitionStatus(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    state: str  # idle | starting | running | stopping | failed
    model_loaded: bool = False
    camera_active: bool = False
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    last_error: Optional[str] = None
    last_event: Optional[RecognitionEventOut] = None
    events_processed: int = 0
    model_stale: bool = False
    model_stale_since: Optional[datetime] = None
    stale_predictions_seen: int = 0
