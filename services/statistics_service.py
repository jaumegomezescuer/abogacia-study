"""Compone las estadísticas de progreso a partir de los repositorios."""
from __future__ import annotations

from repositories import test_repository


def get_summary(client) -> dict:
    totals = test_repository.answer_totals(client)
    answered = totals["correct"] + totals["incorrect"] + totals["blank"]
    non_blank = totals["correct"] + totals["incorrect"]
    accuracy_pct = (totals["correct"] / non_blank * 100) if non_blank else None

    return {
        "answered": answered,
        "correct": totals["correct"],
        "incorrect": totals["incorrect"],
        "blank": totals["blank"],
        "accuracy_pct": accuracy_pct,
        "average_penalized_score": test_repository.average_penalized_score(client),
        "average_response_time_seconds": test_repository.average_response_time_seconds(client),
        "by_area": {
            area: test_repository.accuracy_by_area(client, area) for area in ("common", "criminal")
        },
        "by_topic": test_repository.accuracy_by_topic(client),
        "by_difficulty": test_repository.accuracy_by_difficulty(client),
        "by_question_type": test_repository.accuracy_by_question_type(client),
        "recent_sessions": list(reversed(test_repository.list_sessions(client, limit=20))),
        "most_failed_questions": test_repository.most_failed_questions(client, limit=10),
        "correct_with_low_confidence": test_repository.count_correct_with_low_confidence(client),
        "mock_exam_count": test_repository.count_sessions(client, test_type="mock_exam"),
    }
