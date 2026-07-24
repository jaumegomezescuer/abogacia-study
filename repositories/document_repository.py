"""Acceso a datos de la tabla `documents`."""
from __future__ import annotations

from typing import Any, Optional

from services.database import execute, row_to_dict, rows_to_dicts

_COLUMNS = (
    "id", "original_name", "stored_name", "file_type", "area", "topic",
    "material_type", "language", "page_count", "text_content",
    "processing_status", "processing_error", "created_at", "updated_at",
)


def create(client, *, original_name: str, stored_name: str, file_type: str,
           file_content: Optional[bytes], area: str, topic: Optional[str],
           material_type: str, language: str, page_count: Optional[int],
           text_content: Optional[str], processing_status: str,
           processing_error: Optional[str]) -> int:
    result = execute(
        client,
        """
        INSERT INTO documents (
            original_name, stored_name, file_type, file_content, area, topic,
            material_type, language, page_count, text_content,
            processing_status, processing_error, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        [original_name, stored_name, file_type, file_content, area, topic,
         material_type, language, page_count, text_content,
         processing_status, processing_error],
    )
    return result.last_insert_rowid


def get_by_id(client, document_id: int, *, include_content: bool = False) -> Optional[dict]:
    columns = ", ".join(_COLUMNS) + (", file_content" if include_content else "")
    result = execute(client, f"SELECT {columns} FROM documents WHERE id = ?", [document_id])
    return row_to_dict(result)


def list_all(client, *, area: Optional[str] = None, material_type: Optional[str] = None,
             language: Optional[str] = None, search: Optional[str] = None) -> list[dict]:
    columns = ", ".join(_COLUMNS)
    sql = f"SELECT {columns} FROM documents"
    conditions: list[str] = []
    params: list[Any] = []
    if area:
        conditions.append("area = ?")
        params.append(area)
    if material_type:
        conditions.append("material_type = ?")
        params.append(material_type)
    if language:
        conditions.append("language = ?")
        params.append(language)
    if search:
        conditions.append("(original_name LIKE ? OR topic LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like])
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY created_at DESC"
    return rows_to_dicts(execute(client, sql, params))


def update_processing_result(client, document_id: int, *, page_count: Optional[int],
                              text_content: Optional[str], processing_status: str,
                              processing_error: Optional[str]) -> None:
    execute(
        client,
        """
        UPDATE documents
        SET page_count = ?, text_content = ?, processing_status = ?,
            processing_error = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        [page_count, text_content, processing_status, processing_error, document_id],
    )


def delete(client, document_id: int, *, keep_questions: bool = True) -> int:
    """Elimina un documento. Devuelve cuántas preguntas quedaron afectadas."""
    affected = execute(
        client, "SELECT COUNT(*) FROM questions WHERE document_id = ?", [document_id]
    ).rows[0][0]
    if affected:
        if keep_questions:
            execute(client, "UPDATE questions SET document_id = NULL WHERE document_id = ?", [document_id])
        else:
            execute(client, "DELETE FROM questions WHERE document_id = ?", [document_id])
    execute(client, "DELETE FROM documents WHERE id = ?", [document_id])
    return affected


def count(client) -> int:
    return execute(client, "SELECT COUNT(*) FROM documents").rows[0][0]


def count_linked_questions(client, document_id: int) -> int:
    return execute(client, "SELECT COUNT(*) FROM questions WHERE document_id = ?", [document_id]).rows[0][0]


def distinct_topics(client, area: Optional[str] = None) -> list[str]:
    if area:
        result = execute(
            client,
            "SELECT DISTINCT topic FROM documents WHERE area = ? AND topic IS NOT NULL AND topic != '' ORDER BY topic",
            [area],
        )
    else:
        result = execute(
            client,
            "SELECT DISTINCT topic FROM documents WHERE topic IS NOT NULL AND topic != '' ORDER BY topic",
        )
    return [row[0] for row in result.rows]
