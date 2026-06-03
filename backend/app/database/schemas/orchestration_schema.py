"""Pydantic schemas for the orchestration layer."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from app.database.schemas.recognition_schema import (
    RecognitionEventOut,
    RecognitionStatus,
)


class IngestionStatus(BaseModel):
    alive: bool
    queue_size: int


class ModelHealth(BaseModel):
    """Top-level surface for stale-model detection.

    Mirrors the runtime's sticky flags so the dashboard can render a global
    'retraining required' warning without inspecting nested recognition state.
    """

    model_config = ConfigDict(protected_namespaces=())

    model_stale: bool = False
    model_stale_since: Optional[str] = None
    stale_predictions_seen: int = 0


class RecognitionDiagnostics(BaseModel):
    """Similarity distribution stats for threshold calibration.

    ``metric_stats`` contains unified similarity values in [0, 1] where
    higher = better match, regardless of the active recognition backend.
    """

    metric_stats: Optional[Dict[str, Any]] = None


class ActiveSessionInfo(BaseModel):
    """Metadata about the currently running attendance session."""

    session_id: int
    class_id: int
    session_name: str
    allowed_count: int = 0


class SessionStatus(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    session_state: str  # idle | starting | running | stopping | failed
    recognition: RecognitionStatus
    ingestion: IngestionStatus
    active_model: Optional[Dict[str, Any]] = None
    active_session: Optional[ActiveSessionInfo] = None
    recent_events: List[RecognitionEventOut] = []
    last_error: Optional[str] = None
    model_health: ModelHealth = ModelHealth()
    diagnostics: RecognitionDiagnostics = RecognitionDiagnostics()
    runtime_metrics: Optional[Dict[str, Any]] = None
