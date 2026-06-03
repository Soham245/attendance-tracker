"""Pydantic schemas for attendance sessions."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SessionStartRequest(BaseModel):
    """Body for POST /session/start."""
    class_id: int = Field(description="Academic class to scope this session to")
    session_name: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Display name. Auto-generated if omitted.",
    )


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_name: str
    class_id: int
    class_code: Optional[str] = None
    faculty_id: int
    faculty_name: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str
    attendance_count: int = 0

    @classmethod
    def from_orm_with_relations(cls, session, attendance_count: int = 0) -> "SessionResponse":
        data = cls.model_validate(session)
        if session.academic_class is not None:
            data.class_code = session.academic_class.class_code
        if session.faculty is not None:
            data.faculty_name = session.faculty.username
        data.attendance_count = attendance_count
        return data


class SessionListResponse(BaseModel):
    items: List[SessionResponse]
    total: int
