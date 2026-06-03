"""Standardized API response envelope.

Shape (success and error both share `success` + `message`):
    { "success": true,  "message": "...", "data": {...} }
    { "success": false, "message": "...", "errors": [{code, message, field?}] }
"""
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: Optional[T] = None, message: Optional[str] = None) -> "APIResponse[T]":
        return cls(success=True, message=message, data=data)


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: Optional[List[ErrorDetail]] = None
