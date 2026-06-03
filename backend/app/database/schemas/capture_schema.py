"""Pydantic schemas for the dataset capture runtime."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.config.settings import settings


class CaptureStartRequest(BaseModel):
    """Payload for POST /capture/start.

    Target sample count is now computed from phases × samples_per_phase.
    The guided enrollment flow owns the total; callers just specify the student.

    When *replace* is True the student's existing dataset is wiped before
    capture begins, ensuring every enrollment session produces a clean dataset.
    """
    student_id: int = Field(..., ge=1)
    replace: bool = Field(False, description="Wipe existing dataset before capturing")


class CaptureStatus(BaseModel):
    """Polling-friendly snapshot of the capture runtime."""
    state: str  # idle | starting | capturing | stopping | completed | failed
    student_id: Optional[int] = None
    samples_collected: int = 0
    target_samples: int = 0
    camera_active: bool = False
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    last_error: Optional[str] = None
    last_sample_filename: Optional[str] = None
    dataset_image_count: int = 0
    # Guided enrollment fields
    phase_index: int = 0
    phase_id: Optional[str] = None
    phase_instruction: Optional[str] = None
    samples_in_phase: int = 0
    samples_per_phase: int = 0
    quality_guidance: str = ""
    quality_acceptable: bool = False
