"""Pydantic schemas for user management."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateFacultyRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class UpdateFacultyRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=64)
    email: Optional[str] = Field(None, min_length=5, max_length=255)
    password: Optional[str] = Field(None, min_length=6, max_length=128)


class ToggleActiveRequest(BaseModel):
    active: bool


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    must_change_password: bool = False
    created_at: datetime


class UserListResponse(BaseModel):
    users: List[UserOut]
    total: int
