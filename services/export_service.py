"""Exportación de datos (preguntas y base de datos completa) para copias de seguridad."""
from __future__ import annotations

import base64
import csv
import io
import json

from repositories import document_repository, question_repository, settings_repository
from services.database import execute, rows_to_dicts

QUESTION_EXPORT_FIELDS = [
    "id", "document_id", "area", "topic", "subtopic", "language", "question_type",
    "source_type", "difficulty", "statement", "option_a", "option_b", "option_c", "option_d",
    "correct_option", "explanation", "incorrect_explanations", "source_reference", "source_page",
    "legal_reference", "is_active", "exam_name", "exam_year", "exam_call", "status",
    "created_at", "updated_at",
]


def export_questions_csv(client) -> bytes:
    questions = question_repository.list_questions(client, is_active=None, exclude_annulled=False, limit=None)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=QUESTION_EXPORT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for question in questions:
        writer.writerow(question)
    return buffer.getvalue().encode("utf-8-sig")


def export_questions_json(client) -> bytes:
    questions = question_repository.list_questions(client, is_active=None, exclude_annulled=False, limit=None)
    return json.dumps(questions, ensure_ascii=False, indent=2).encode("utf-8")


def export_full_database_json(client) -> bytes:
    """Exporta todas las tablas, incluyendo los archivos originales en base64."""
    documents = []
    for doc in document_repository.list_all(client):
        full = document_repository.get_by_id(client, doc["id"], include_content=True)
        content = full.get("file_content")
        full["file_content_base64"] = base64.b64encode(content).decode("ascii") if content else None
        full.pop("file_content", None)
        documents.append(full)

    questions = question_repository.list_questions(client, is_active=None, exclude_annulled=False, limit=None)
    sessions = rows_to_dicts(execute(client, "SELECT * FROM test_sessions"))
    answers = rows_to_dicts(execute(client, "SELECT * FROM test_answers"))
    progress = rows_to_dicts(execute(client, "SELECT * FROM question_progress"))
    settings = settings_repository.get_all(client)

    payload = {
        "documents": documents,
        "questions": questions,
        "test_sessions": sessions,
        "test_answers": answers,
        "question_progress": progress,
        "app_settings": settings,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def delete_all_data(client) -> None:
    """Borra todos los datos de la aplicación (documentos, preguntas, tests, progreso, ajustes)."""
    for table in (
        "test_answers", "test_sessions", "question_progress", "questions",
        "documents", "app_settings", "schema_migrations",
    ):
        execute(client, f"DELETE FROM {table}")
    from services.database import run_migrations
    run_migrations(client)
