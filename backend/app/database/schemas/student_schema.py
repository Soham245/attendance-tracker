"""Pydantic schemas for the Student domain."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StudentBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    roll_number: str = Field(min_length=1, max_length=32)
    department: Optional[str] = Field(default=None, max_length=64)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=32)
    class_id: Optional[int] = Field(default=None, description="Academic class assignment")


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    """All fields optional — PATCH-style partial update."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    roll_number: Optional[str] = Field(default=None, min_length=1, max_length=32)
    department: Optional[str] = Field(default=None, max_length=64)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=32)
    class_id: Optional[int] = Field(default=None, description="Academic class assignment")


class StudentResponse(StudentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: Optional[int] = None
    class_code: Optional[str] = Field(default=None, description="From joined academic class")
    dataset_path: Optional[str] = None
    training_required: bool = False
    created_at: datetime

    # Lifecycle fields
    status: str = "active"
    graduated_at: Optional[datetime] = None
    last_class_id: Optional[int] = None
    last_class_code: Optional[str] = Field(default=None, description="From joined last class")
    lifecycle_batch_id: Optional[str] = None


    @classmethod
    def from_orm_with_class(cls, student) -> "StudentResponse":
        """Build response with class_code resolved from the joined relationship."""
        data = cls.model_validate(student)
        if student.academic_class is not None:
            data.class_code = student.academic_class.class_code
        if getattr(student, "last_class", None) is not None:
            data.last_class_code = student.last_class.class_code
        return data


class StudentListResponse(BaseModel):
    items: List[StudentResponse]
    total: int
