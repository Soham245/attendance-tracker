"""Pydantic schemas for the AcademicClass domain."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


def generate_class_code(
    major: str, academic_year: str, year: int, section: str
) -> str:
    """Build the deterministic class code.

    Format: ``{MAJOR}-{start_year}-Y{year}-{section}``

    ``academic_year`` is expected as ``"2026-27"``; only the start year
    (the part before the dash) is embedded in the code.

    Examples::

        MCA, 2026-27, 1, A  ->  MCA-2026-Y1-A
        BCA, 2027-28, 2, B  ->  BCA-2027-Y2-B
    """
    start_year = academic_year.split("-")[0].strip()
    return f"{major.upper()}-{start_year}-Y{year}-{section.upper()}"


class ClassCreate(BaseModel):
    major: str = Field(min_length=1, max_length=64)
    year: int = Field(ge=1, le=6)
    section: str = Field(min_length=1, max_length=8)
    academic_year: str = Field(
        min_length=4,
        max_length=16,
        pattern=r"^\d{4}-\d{2,4}$",
        description='Academic year in "YYYY-YY" format (e.g. "2026-27")',
    )
    class_code: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Auto-generated if omitted. Admin may override.",
    )


class ClassUpdate(BaseModel):
    """All fields optional — PATCH-style partial update."""

    major: Optional[str] = Field(default=None, min_length=1, max_length=64)
    year: Optional[int] = Field(default=None, ge=1, le=6)
    section: Optional[str] = Field(default=None, min_length=1, max_length=8)
    academic_year: Optional[str] = Field(
        default=None,
        min_length=4,
        max_length=16,
        pattern=r"^\d{4}-\d{2,4}$",
    )
    class_code: Optional[str] = Field(default=None, max_length=32)
    is_active: Optional[bool] = None


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_code: str
    major: str
    year: int
    section: str
    academic_year: str
    is_active: bool
    created_at: datetime


class ClassListResponse(BaseModel):
    items: List[ClassResponse]
    total: int
