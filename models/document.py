from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from models.base import BaseModel

AREAS = ("common", "criminal")
MATERIAL_TYPES = ("notes", "official_exam", "legislation", "summary", "case_study", "presentation", "other")
PROCESSING_STATUSES = ("pending", "processed", "error")


@dataclass
class Document(BaseModel):
    id: Optional[int]
    original_name: str
    stored_name: str
    file_type: str
    area: str
    topic: Optional[str]
    material_type: str
    language: str
    page_count: Optional[int]
    text_content: Optional[str]
    processing_status: str
    processing_error: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    file_content: Optional[bytes] = None
