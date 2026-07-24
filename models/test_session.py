from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from models.base import BaseModel

TEST_TYPES = ("practice", "custom", "mock_exam", "error_review", "official")
CONFIDENCE_LEVELS = ("sure", "doubtful", "guess", "not_set")


@dataclass
class TestSession(BaseModel):
    id: Optional[int]
    test_type: str
    area: Optional[str] = None
    language: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    total_questions: int = 0
    correct_answers: int = 0
    incorrect_answers: int = 0
    blank_answers: int = 0
    raw_score: Optional[float] = None
    penalized_score: Optional[float] = None
    duration_seconds: Optional[int] = None
    completed: int = 0


@dataclass
class TestAnswer(BaseModel):
    id: Optional[int]
    test_session_id: int
    question_id: int
    selected_option: Optional[str] = None
    is_correct: Optional[int] = None
    is_blank: int = 0
    confidence_level: str = "not_set"
    response_time_seconds: Optional[float] = None
    answered_at: Optional[str] = None


@dataclass
class QuestionProgress(BaseModel):
    id: Optional[int]
    question_id: int
    times_seen: int = 0
    times_correct: int = 0
    times_incorrect: int = 0
    times_blank: int = 0
    last_answered_at: Optional[str] = None
    last_result: Optional[str] = None
    marked_for_review: int = 0
    next_review_at: Optional[str] = None
