"""Acceso a datos de sesiones de test, respuestas y progreso por pregunta."""
from __future__ import annotations

from typing import Any, Optional

from services.database import execute, row_to_dict, rows_to_dicts


def create_session(client, *, test_type: str, area: Optional[str], language: Optional[str],
                    total_questions: int = 0) -> int:
    result = execute(
        client,
        """
        INSERT INTO test_sessions (test_type, area, language, total_questions)
        VALUES (?, ?, ?, ?)
        """,
        [test_type, area, language, total_questions],
    )
    return result.last_insert_rowid


def finish_session(client, session_id: int, *, total_questions: int, correct_answers: int,
                    incorrect_answers: int, blank_answers: int, raw_score: float,
                    penalized_score: float, duration_seconds: Optional[int]) -> None:
    execute(
        client,
        """
        UPDATE test_sessions
        SET finished_at = CURRENT_TIMESTAMP, total_questions = ?, correct_answers = ?,
            incorrect_answers = ?, blank_answers = ?, raw_score = ?, penalized_score = ?,
            duration_seconds = ?, completed = 1
        WHERE id = ?
        """,
        [total_questions, correct_answers, incorrect_answers, blank_answers, raw_score,
         penalized_score, duration_seconds, session_id],
    )


def get_session(client, session_id: int) -> Optional[dict]:
    return row_to_dict(execute(client, "SELECT * FROM test_sessions WHERE id = ?", [session_id]))


def list_sessions(client, *, limit: Optional[int] = None, only_completed: bool = True) -> list[dict]:
    sql = "SELECT * FROM test_sessions"
    if only_completed:
        sql += " WHERE completed = 1"
    sql += " ORDER BY started_at DESC"
    params: list[Any] = []
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return rows_to_dicts(execute(client, sql, params))


def count_sessions(client, *, test_type: Optional[str] = None) -> int:
    if test_type:
        return execute(
            client, "SELECT COUNT(*) FROM test_sessions WHERE completed = 1 AND test_type = ?", [test_type]
        ).rows[0][0]
    return execute(client, "SELECT COUNT(*) FROM test_sessions WHERE completed = 1").rows[0][0]


def create_answer(client, *, test_session_id: int, question_id: int, selected_option: Optional[str],
                   is_correct: Optional[bool], is_blank: bool, confidence_level: str,
                   response_time_seconds: Optional[float]) -> int:
    result = execute(
        client,
        """
        INSERT INTO test_answers (
            test_session_id, question_id, selected_option, is_correct, is_blank,
            confidence_level, response_time_seconds
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [test_session_id, question_id, selected_option,
         None if is_correct is None else (1 if is_correct else 0),
         1 if is_blank else 0, confidence_level, response_time_seconds],
    )
    return result.last_insert_rowid


def list_answers_for_session(client, test_session_id: int) -> list[dict]:
    return rows_to_dicts(
        execute(client, "SELECT * FROM test_answers WHERE test_session_id = ? ORDER BY id", [test_session_id])
    )


def get_question_progress(client, question_id: int) -> Optional[dict]:
    return row_to_dict(
        execute(client, "SELECT * FROM question_progress WHERE question_id = ?", [question_id])
    )


def record_answer_progress(client, question_id: int, *, result: str) -> None:
    """Actualiza question_progress tras responder. `result` es 'correct', 'incorrect' o 'blank'."""
    existing = get_question_progress(client, question_id)
    if existing is None:
        execute(
            client,
            """
            INSERT INTO question_progress (
                question_id, times_seen, times_correct, times_incorrect, times_blank,
                last_answered_at, last_result
            ) VALUES (?, 1, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """,
            [question_id, 1 if result == "correct" else 0, 1 if result == "incorrect" else 0,
             1 if result == "blank" else 0, result],
        )
        return
    execute(
        client,
        """
        UPDATE question_progress
        SET times_seen = times_seen + 1,
            times_correct = times_correct + ?,
            times_incorrect = times_incorrect + ?,
            times_blank = times_blank + ?,
            last_answered_at = CURRENT_TIMESTAMP,
            last_result = ?
        WHERE question_id = ?
        """,
        [1 if result == "correct" else 0, 1 if result == "incorrect" else 0,
         1 if result == "blank" else 0, result, question_id],
    )


def set_marked_for_review(client, question_id: int, marked: bool) -> None:
    existing = get_question_progress(client, question_id)
    if existing is None:
        execute(
            client,
            "INSERT INTO question_progress (question_id, marked_for_review) VALUES (?, ?)",
            [question_id, 1 if marked else 0],
        )
        return
    execute(
        client,
        "UPDATE question_progress SET marked_for_review = ? WHERE question_id = ?",
        [1 if marked else 0, question_id],
    )


def reset_question_progress(client, question_id: int) -> None:
    execute(client, "DELETE FROM question_progress WHERE question_id = ?", [question_id])


def mark_as_mastered(client, question_id: int) -> None:
    """Deja de contar los fallos pasados de cara al repaso, sin borrar el historial de aciertos."""
    execute(
        client,
        "UPDATE question_progress SET times_incorrect = 0, marked_for_review = 0 WHERE question_id = ?",
        [question_id],
    )


def accuracy_by_area(client, area: str) -> tuple[int, int]:
    """Devuelve (respuestas_correctas, respuestas_totales_no_blanco) para un área."""
    result = execute(
        client,
        """
        SELECT COALESCE(SUM(ta.is_correct), 0), COUNT(*)
        FROM test_answers ta
        JOIN questions q ON q.id = ta.question_id
        WHERE ta.is_blank = 0 AND q.area = ?
        """,
        [area],
    )
    row = result.rows[0]
    return int(row[0] or 0), int(row[1] or 0)


def global_accuracy(client) -> tuple[int, int]:
    result = execute(
        client,
        "SELECT COALESCE(SUM(is_correct), 0), COUNT(*) FROM test_answers WHERE is_blank = 0",
    )
    row = result.rows[0]
    return int(row[0] or 0), int(row[1] or 0)


def count_pending_review(client) -> int:
    return execute(
        client,
        "SELECT COUNT(*) FROM question_progress WHERE times_incorrect > times_correct OR marked_for_review = 1",
    ).rows[0][0]


def answer_totals(client) -> dict:
    """Cuenta global de respuestas: correctas, incorrectas y en blanco."""
    result = execute(
        client,
        """
        SELECT
            COALESCE(SUM(CASE WHEN is_blank = 0 AND is_correct = 1 THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN is_blank = 0 AND is_correct = 0 THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN is_blank = 1 THEN 1 ELSE 0 END), 0)
        FROM test_answers
        """,
    )
    correct, incorrect, blank = result.rows[0]
    return {"correct": int(correct or 0), "incorrect": int(incorrect or 0), "blank": int(blank or 0)}


def accuracy_by_topic(client) -> list[dict]:
    return rows_to_dicts(execute(
        client,
        """
        SELECT q.topic AS topic, COALESCE(SUM(ta.is_correct), 0) AS correct, COUNT(*) AS total
        FROM test_answers ta JOIN questions q ON q.id = ta.question_id
        WHERE ta.is_blank = 0 AND q.topic IS NOT NULL AND q.topic != ''
        GROUP BY q.topic ORDER BY total DESC
        """,
    ))


def accuracy_by_difficulty(client) -> list[dict]:
    return rows_to_dicts(execute(
        client,
        """
        SELECT q.difficulty AS difficulty, COALESCE(SUM(ta.is_correct), 0) AS correct, COUNT(*) AS total
        FROM test_answers ta JOIN questions q ON q.id = ta.question_id
        WHERE ta.is_blank = 0
        GROUP BY q.difficulty ORDER BY total DESC
        """,
    ))


def accuracy_by_question_type(client) -> list[dict]:
    return rows_to_dicts(execute(
        client,
        """
        SELECT q.question_type AS question_type, COALESCE(SUM(ta.is_correct), 0) AS correct, COUNT(*) AS total
        FROM test_answers ta JOIN questions q ON q.id = ta.question_id
        WHERE ta.is_blank = 0
        GROUP BY q.question_type ORDER BY total DESC
        """,
    ))


def average_response_time_seconds(client) -> Optional[float]:
    row = execute(
        client, "SELECT AVG(response_time_seconds) FROM test_answers WHERE response_time_seconds IS NOT NULL",
    ).rows[0]
    return float(row[0]) if row[0] is not None else None


def average_penalized_score(client) -> Optional[float]:
    row = execute(client, "SELECT AVG(penalized_score) FROM test_sessions WHERE completed = 1").rows[0]
    return float(row[0]) if row[0] is not None else None


def most_failed_questions(client, limit: int = 10) -> list[dict]:
    return rows_to_dicts(execute(
        client,
        """
        SELECT q.id, q.statement, q.topic, q.area, qp.times_incorrect, qp.times_seen
        FROM question_progress qp JOIN questions q ON q.id = qp.question_id
        WHERE qp.times_incorrect > 0
        ORDER BY qp.times_incorrect DESC, qp.times_seen DESC LIMIT ?
        """,
        [limit],
    ))


def count_correct_with_low_confidence(client) -> int:
    return execute(
        client,
        "SELECT COUNT(*) FROM test_answers WHERE is_correct = 1 AND confidence_level IN ('doubtful', 'guess')",
    ).rows[0][0]
