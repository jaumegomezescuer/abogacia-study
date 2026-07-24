"""Cálculo de puntuación de tests y simulacros.

puntuación = aciertos - errores * penalización (las preguntas en blanco no
suman ni restan, salvo que se configure explícitamente lo contrario).
"""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_CORRECT_SCORE = 1.0
DEFAULT_INCORRECT_PENALTY = 1.0 / 3.0
DEFAULT_BLANK_SCORE = 0.0


def calculate_score(*, correct: int, incorrect: int, blank: int = 0,
                     correct_score: float = DEFAULT_CORRECT_SCORE,
                     incorrect_penalty: float = DEFAULT_INCORRECT_PENALTY,
                     blank_score: float = DEFAULT_BLANK_SCORE) -> float:
    return (correct * correct_score) - (incorrect * incorrect_penalty) + (blank * blank_score)


@dataclass
class PartScore:
    correct: int
    incorrect: int
    blank: int
    raw_score: float
    scored_total: int
    normalized_0_10: float


@dataclass
class MockExamScore:
    common: PartScore
    criminal: PartScore
    common_weight: float
    criminal_weight: float
    total_score_0_10: float


def _part_score(*, correct: int, incorrect: int, blank: int, correct_score: float,
                 incorrect_penalty: float, blank_score: float) -> PartScore:
    raw_score = calculate_score(
        correct=correct, incorrect=incorrect, blank=blank,
        correct_score=correct_score, incorrect_penalty=incorrect_penalty, blank_score=blank_score,
    )
    scored_total = correct + incorrect + blank
    normalized = (raw_score / scored_total * 10) if scored_total else 0.0
    return PartScore(
        correct=correct, incorrect=incorrect, blank=blank, raw_score=raw_score,
        scored_total=scored_total, normalized_0_10=normalized,
    )


def calculate_mock_exam_score(
    *, common_correct: int, common_incorrect: int, common_blank: int,
    criminal_correct: int, criminal_incorrect: int, criminal_blank: int,
    correct_score: float = DEFAULT_CORRECT_SCORE,
    incorrect_penalty: float = DEFAULT_INCORRECT_PENALTY,
    blank_score: float = DEFAULT_BLANK_SCORE,
    common_weight: float = 2.0 / 3.0,
    criminal_weight: float = 1.0 / 3.0,
) -> MockExamScore:
    common = _part_score(
        correct=common_correct, incorrect=common_incorrect, blank=common_blank,
        correct_score=correct_score, incorrect_penalty=incorrect_penalty, blank_score=blank_score,
    )
    criminal = _part_score(
        correct=criminal_correct, incorrect=criminal_incorrect, blank=criminal_blank,
        correct_score=correct_score, incorrect_penalty=incorrect_penalty, blank_score=blank_score,
    )
    total = common.normalized_0_10 * common_weight + criminal.normalized_0_10 * criminal_weight
    return MockExamScore(
        common=common, criminal=criminal,
        common_weight=common_weight, criminal_weight=criminal_weight,
        total_score_0_10=total,
    )
