"""Pydantic schemas for the attendance domain."""
from datetime import date as date_t, datetime
from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class RecognitionEventIn(BaseModel):
    """Shape of an event consumed from the recognition runtime."""
    student_id: int
    confidence: float
    recognized_at: datetime


class AttendanceStudent(BaseModel):
    """Operator-facing identity block embedded in attendance responses.

    `student_code` mirrors the student's roll number — the field is renamed in
    the API surface because that's the externally-meaningful identifier; the
    DB column name is an implementation detail.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    name: str
    student_code: str = Field(
        validation_alias=AliasChoices("student_code", "roll_number"),
    )


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    student: Optional[AttendanceStudent] = None
    recognized_at: datetime
    confidence: float
    status: str
    created_at: datetime


class AttendanceListResponse(BaseModel):
    items: List[AttendanceResponse]
    total: int


class AttendanceQuery(BaseModel):
    """Query parameters (FastAPI binds these from the query string)."""
    student_id: Optional[int] = None
    on_date: Optional[date_t] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)
