"""Conexión y esquema de la base de datos (Turso / SQLite).

Toda la aplicación pasa por aquí para hablar con la base de datos. Ninguna
página de Streamlit ni ningún repositorio debe crear su propio cliente de
libsql: siempre a través de `get_client()` (en producción/local con
Streamlit) o `create_test_client()` (en pruebas).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Sequence

import libsql_client
import streamlit as st

logger = logging.getLogger("abogacia")


class DatabaseError(Exception):
    """Error de acceso a datos comprensible para mostrar al usuario."""


# Cada elemento es una "migración": una lista de sentencias SQL que se
# ejecutan una sola vez, en orden, y se registran en `schema_migrations`.
# Añadir cambios de esquema futuros como una migración nueva al final de
# esta lista, nunca modificando las ya aplicadas.
_MIGRATIONS: list[list[str]] = [
    [
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_content BLOB,
            area TEXT NOT NULL CHECK (area IN ('common', 'criminal')),
            topic TEXT,
            material_type TEXT NOT NULL DEFAULT 'other',
            language TEXT NOT NULL DEFAULT 'es',
            page_count INTEGER,
            text_content TEXT,
            processing_status TEXT NOT NULL DEFAULT 'pending'
                CHECK (processing_status IN ('pending', 'processed', 'error')),
            processing_error TEXT,
            created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
            updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
            area TEXT NOT NULL CHECK (area IN ('common', 'criminal')),
            topic TEXT,
            subtopic TEXT,
            language TEXT NOT NULL DEFAULT 'es',
            question_type TEXT NOT NULL DEFAULT 'theoretical'
                CHECK (question_type IN
                    ('theoretical', 'practical_case', 'deadline', 'competence', 'mixed')),
            source_type TEXT NOT NULL CHECK (source_type IN ('official', 'manual')),
            difficulty TEXT NOT NULL DEFAULT 'intermediate'
                CHECK (difficulty IN ('basic', 'intermediate', 'exam', 'advanced')),
            statement TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL CHECK (correct_option IN ('A', 'B', 'C', 'D')),
            explanation TEXT,
            incorrect_explanations TEXT,
            source_reference TEXT,
            source_page TEXT,
            legal_reference TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            exam_name TEXT,
            exam_year INTEGER,
            exam_call TEXT,
            status TEXT NOT NULL DEFAULT 'valid' CHECK (status IN ('valid', 'annulled', 'reserve')),
            created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
            updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS test_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_type TEXT NOT NULL
                CHECK (test_type IN ('practice', 'custom', 'mock_exam', 'error_review', 'official')),
            area TEXT,
            language TEXT,
            started_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
            finished_at TEXT,
            total_questions INTEGER NOT NULL DEFAULT 0,
            correct_answers INTEGER NOT NULL DEFAULT 0,
            incorrect_answers INTEGER NOT NULL DEFAULT 0,
            blank_answers INTEGER NOT NULL DEFAULT 0,
            raw_score REAL,
            penalized_score REAL,
            duration_seconds INTEGER,
            completed INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS test_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_session_id INTEGER NOT NULL REFERENCES test_sessions(id) ON DELETE CASCADE,
            question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            selected_option TEXT,
            is_correct INTEGER,
            is_blank INTEGER NOT NULL DEFAULT 0,
            confidence_level TEXT NOT NULL DEFAULT 'not_set'
                CHECK (confidence_level IN ('sure', 'doubtful', 'guess', 'not_set')),
            response_time_seconds REAL,
            answered_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS question_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL UNIQUE REFERENCES questions(id) ON DELETE CASCADE,
            times_seen INTEGER NOT NULL DEFAULT 0,
            times_correct INTEGER NOT NULL DEFAULT 0,
            times_incorrect INTEGER NOT NULL DEFAULT 0,
            times_blank INTEGER NOT NULL DEFAULT 0,
            last_answered_at TEXT,
            last_result TEXT,
            marked_for_review INTEGER NOT NULL DEFAULT 0,
            next_review_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_questions_area ON questions(area)",
        "CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic)",
        "CREATE INDEX IF NOT EXISTS idx_questions_source ON questions(source_type)",
        "CREATE INDEX IF NOT EXISTS idx_questions_active ON questions(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_documents_area ON documents(area)",
        "CREATE INDEX IF NOT EXISTS idx_test_answers_session ON test_answers(test_session_id)",
        "CREATE INDEX IF NOT EXISTS idx_test_answers_question ON test_answers(question_id)",
        "CREATE INDEX IF NOT EXISTS idx_question_progress_question ON question_progress(question_id)",
    ],
]


def _read_secrets() -> tuple[str, Optional[str]]:
    try:
        url = st.secrets["TURSO_DATABASE_URL"]
    except Exception as exc:  # secrets.toml ausente o incompleto
        raise DatabaseError(
            "Faltan las credenciales de Turso. Copia "
            ".streamlit/secrets.toml.example a .streamlit/secrets.toml "
            "(en local) o configura los 'Secrets' de tu app en Streamlit "
            "Community Cloud, con TURSO_DATABASE_URL y TURSO_AUTH_TOKEN."
        ) from exc
    if not url:
        raise DatabaseError("TURSO_DATABASE_URL está vacío en la configuración.")
    token = st.secrets.get("TURSO_AUTH_TOKEN") or None
    return url, token


def run_migrations(client: "libsql_client.ClientSync") -> None:
    """Crea las tablas que falten. Es seguro llamarla en cada arranque."""
    client.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version INTEGER PRIMARY KEY, "
        "applied_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP))"
    )
    applied = {row[0] for row in client.execute("SELECT version FROM schema_migrations").rows}
    for version, statements in enumerate(_MIGRATIONS, start=1):
        if version in applied:
            continue
        for statement in statements:
            client.execute(statement)
        client.execute("INSERT INTO schema_migrations (version) VALUES (?)", [version])
        logger.info("Migración de base de datos aplicada: versión %s", version)


def create_test_client(path: str) -> "libsql_client.ClientSync":
    """Cliente contra un archivo SQLite local, pensado para pruebas."""
    client = libsql_client.create_client_sync(url=f"file:{path}")
    run_migrations(client)
    return client


@st.cache_resource(show_spinner="Conectando con la base de datos...")
def get_client() -> "libsql_client.ClientSync":
    """Cliente compartido (cacheado) contra Turso, para toda la app."""
    url, token = _read_secrets()
    if token:
        client = libsql_client.create_client_sync(url=url, auth_token=token)
    else:
        client = libsql_client.create_client_sync(url=url)
    try:
        run_migrations(client)
    except Exception as exc:
        logger.exception("Error inicializando el esquema de la base de datos")
        raise DatabaseError(f"No se pudo preparar la base de datos: {exc}") from exc
    return client


def execute(client: "libsql_client.ClientSync", sql: str, args: Optional[Sequence[Any]] = None):
    """Ejecuta una sentencia SQL y traduce errores a DatabaseError."""
    try:
        return client.execute(sql, list(args) if args is not None else [])
    except DatabaseError:
        raise
    except Exception as exc:
        logger.exception("Error ejecutando SQL: %s", sql)
        raise DatabaseError(str(exc)) from exc


def rows_to_dicts(result_set) -> list[dict]:
    """Convierte un ResultSet de libsql en una lista de diccionarios."""
    columns = result_set.columns
    return [dict(zip(columns, row)) for row in result_set.rows]


def row_to_dict(result_set) -> Optional[dict]:
    """Devuelve la primera fila como diccionario, o None si no hay filas."""
    rows = rows_to_dicts(result_set)
    return rows[0] if rows else None


def placeholders(count: int) -> str:
    """Genera 'N' marcadores de posición '?' separados por comas, para IN (...)."""
    return ", ".join(["?"] * count)
