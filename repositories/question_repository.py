"""Acceso a datos de la tabla `questions`."""
from __future__ import annotations

from typing import Any, Optional

from services.database import execute, placeholders, row_to_dict, rows_to_dicts

_INSERT_FIELDS = (
    "document_id", "area", "topic", "subtopic", "language", "question_type",
    "source_type", "difficulty", "statement", "option_a", "option_b",
    "option_c", "option_d", "correct_option", "explanation",
    "incorrect_explanations", "source_reference", "source_page",
    "legal_reference", "is_active", "exam_name", "exam_year", "exam_call", "status",
)


_DEFAULTS = {"is_active": 1, "status": "valid"}


def create(client, fields: dict) -> int:
    merged = {**_DEFAULTS, **{k: v for k, v in fields.items() if v is not None or k not in _DEFAULTS}}
    values = [merged.get(name) for name in _INSERT_FIELDS]
    columns_sql = ", ".join(_INSERT_FIELDS)
    values_sql = placeholders(len(_INSERT_FIELDS))
    result = execute(
        client,
        f"INSERT INTO questions ({columns_sql}, updated_at) VALUES ({values_sql}, CURRENT_TIMESTAMP)",
        values,
    )
    return result.last_insert_rowid


def bulk_create(client, list_of_fields: list[dict]) -> list[int]:
    return [create(client, fields) for fields in list_of_fields]


def get_by_id(client, question_id: int) -> Optional[dict]:
    return row_to_dict(execute(client, "SELECT * FROM questions WHERE id = ?", [question_id]))


def update(client, question_id: int, fields: dict) -> None:
    columns = [name for name in _INSERT_FIELDS if name in fields]
    if not columns:
        return
    set_sql = ", ".join(f"{name} = ?" for name in columns)
    values = [fields[name] for name in columns]
    values.append(question_id)
    execute(client, f"UPDATE questions SET {set_sql}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)


def set_active(client, question_id: int, is_active: bool) -> None:
    execute(
        client,
        "UPDATE questions SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        [1 if is_active else 0, question_id],
    )


def delete(client, question_id: int) -> None:
    execute(client, "DELETE FROM questions WHERE id = ?", [question_id])


def _build_filters(*, areas=None, topics=None, languages=None, difficulties=None,
                    question_types=None, source_types=None, document_id=None,
                    statuses=None, is_active: Optional[bool] = True,
                    exclude_ids=None) -> tuple[list[str], list[Any]]:
    conditions: list[str] = []
    params: list[Any] = []

    def _in_clause(column: str, values):
        if values:
            conditions.append(f"{column} IN ({placeholders(len(values))})")
            params.extend(values)

    _in_clause("q.area", areas)
    _in_clause("q.topic", topics)
    _in_clause("q.language", languages)
    _in_clause("q.difficulty", difficulties)
    _in_clause("q.question_type", question_types)
    _in_clause("q.source_type", source_types)
    _in_clause("q.status", statuses)
    if document_id is not None:
        conditions.append("q.document_id = ?")
        params.append(document_id)
    if is_active is not None:
        conditions.append("q.is_active = ?")
        params.append(1 if is_active else 0)
    if exclude_ids:
        conditions.append(f"q.id NOT IN ({placeholders(len(exclude_ids))})")
        params.extend(exclude_ids)
    return conditions, params


def list_questions(client, *, areas=None, topics=None, languages=None, difficulties=None,
                    question_types=None, source_types=None, document_id=None,
                    statuses=None, is_active: Optional[bool] = True,
                    only_never_answered=False, only_failed=False, exclude_ids=None,
                    exclude_annulled: bool = True, order_random=False, limit=None) -> list[dict]:
    conditions, params = _build_filters(
        areas=areas, topics=topics, languages=languages, difficulties=difficulties,
        question_types=question_types, source_types=source_types, document_id=document_id,
        statuses=statuses, is_active=is_active, exclude_ids=exclude_ids,
    )
    if exclude_annulled and not statuses:
        # Las preguntas anuladas no deben aparecer en tests normales, salvo que se pidan explícitamente.
        conditions.append("q.status != 'annulled'")
    joins = ""
    if only_never_answered or only_failed:
        joins = " LEFT JOIN question_progress qp ON qp.question_id = q.id"
        if only_never_answered:
            conditions.append("(qp.times_seen IS NULL OR qp.times_seen = 0)")
        if only_failed:
            conditions.append("COALESCE(qp.times_incorrect, 0) > 0")

    sql = f"SELECT q.* FROM questions q{joins}"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY RANDOM()" if order_random else " ORDER BY q.created_at DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return rows_to_dicts(execute(client, sql, params))


def list_with_progress(client, *, areas=None, topics=None, languages=None,
                        is_active: Optional[bool] = True, only_failed=True,
                        only_multiple_failures=False, only_marked=False) -> list[dict]:
    """Preguntas junto con su progreso (para la página de Errores)."""
    conditions, params = _build_filters(
        areas=areas, topics=topics, languages=languages, is_active=is_active,
    )
    join_type = "JOIN" if only_failed or only_multiple_failures or only_marked else "LEFT JOIN"
    if only_failed:
        conditions.append("COALESCE(qp.times_incorrect, 0) > 0")
    if only_multiple_failures:
        conditions.append("COALESCE(qp.times_incorrect, 0) >= 2")
    if only_marked:
        conditions.append("COALESCE(qp.marked_for_review, 0) = 1")

    sql = f"""
        SELECT q.*,
               COALESCE(qp.times_seen, 0) AS times_seen,
               COALESCE(qp.times_correct, 0) AS times_correct,
               COALESCE(qp.times_incorrect, 0) AS times_incorrect,
               COALESCE(qp.times_blank, 0) AS times_blank,
               qp.last_answered_at AS last_answered_at,
               qp.last_result AS last_result,
               COALESCE(qp.marked_for_review, 0) AS marked_for_review
        FROM questions q
        {join_type} question_progress qp ON qp.question_id = q.id
    """
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY COALESCE(qp.times_incorrect, 0) DESC, q.created_at DESC"
    return rows_to_dicts(execute(client, sql, params))


def count(client, *, areas=None, source_types=None, is_active: Optional[bool] = True) -> int:
    conditions, params = _build_filters(areas=areas, source_types=source_types, is_active=is_active)
    sql = "SELECT COUNT(*) FROM questions q"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    return execute(client, sql, params).rows[0][0]


def distinct_topics(client, area: Optional[str] = None) -> list[str]:
    if area:
        result = execute(
            client,
            "SELECT DISTINCT topic FROM questions WHERE area = ? AND topic IS NOT NULL AND topic != '' ORDER BY topic",
            [area],
        )
    else:
        result = execute(
            client,
            "SELECT DISTINCT topic FROM questions WHERE topic IS NOT NULL AND topic != '' ORDER BY topic",
        )
    return [row[0] for row in result.rows]


def distinct_exam_years(client) -> list[int]:
    result = execute(
        client,
        "SELECT DISTINCT exam_year FROM questions WHERE exam_year IS NOT NULL ORDER BY exam_year DESC",
    )
    return [row[0] for row in result.rows]
