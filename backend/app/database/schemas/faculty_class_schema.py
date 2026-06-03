"""Pydantic schemas for faculty ↔ class assignment."""
from typing import List

from pydantic import BaseModel, Field


class FacultyClassAssignment(BaseModel):
    """One assigned class — returned in GET responses."""
    class_id: int
    class_code: str
    major: str
    year: int
    section: str


class FacultyClassesResponse(BaseModel):
    """Full list of a faculty member's assigned classes."""
    user_id: int
    assignments: List[FacultyClassAssignment]


class FacultyClassesUpdate(BaseModel):
    """Replace the full set of class assignments for a faculty member."""
    class_ids: List[int] = Field(
        description="Complete list of class IDs to assign. "
        "Classes not in this list are unassigned."
    )
