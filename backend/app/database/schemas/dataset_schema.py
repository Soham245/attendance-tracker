"""Pydantic schemas for student dataset images."""
from typing import List

from pydantic import BaseModel


class DatasetImageInfo(BaseModel):
    filename: str
    size_bytes: int


class DatasetListResponse(BaseModel):
    student_id: int
    image_count: int
    images: List[DatasetImageInfo]


class DatasetUploadResponse(BaseModel):
    student_id: int
    image: DatasetImageInfo
    image_count: int
