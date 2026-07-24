from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MockExamConfig:
    """Configuración del simulacro con la configuración actual (sección 15)."""

    common_scored_questions: int = 50
    common_reserve_questions: int = 6
    criminal_scored_questions: int = 25
    criminal_reserve_questions: int = 2
    common_time_minutes: int = 120
    criminal_time_minutes: int = 60
    correct_score: float = 1.0
    incorrect_penalty: float = 1.0 / 3.0
    blank_score: float = 0.0
    common_weight: float = 2.0 / 3.0
    criminal_weight: float = 1.0 / 3.0
    use_annulled_questions: bool = False
    master_note_threshold: float = 5.0
