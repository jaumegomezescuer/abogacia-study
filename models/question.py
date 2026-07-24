from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from models.base import BaseModel

AREAS = ("common", "criminal")
SOURCE_TYPES = ("official", "manual")
QUESTION_TYPES = ("theoretical", "practical_case", "deadline", "competence", "mixed")
DIFFICULTIES = ("basic", "intermediate", "exam", "advanced")
OPTIONS = ("A", "B", "C", "D")
QUESTION_STATUSES = ("valid", "annulled", "reserve")


@dataclass
class Question(BaseModel):
    id: Optional[int]
    area: str
    question_type: str
    source_type: str
    difficulty: str
    statement: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    language: str = "es"
    document_id: Optional[int] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    explanation: Optional[str] = None
    incorrect_explanations: Optional[str] = None
    source_reference: Optional[str] = None
    source_page: Optional[str] = None
    legal_reference: Optional[str] = None
    is_active: int = 1
    exam_name: Optional[str] = None
    exam_year: Optional[int] = None
    exam_call: Optional[str] = None
    status: str = "valid"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def option_text(self, option: str) -> str:
        return {"A": self.option_a, "B": self.option_b, "C": self.option_c, "D": self.option_d}[option]
