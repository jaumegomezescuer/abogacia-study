"""Validación e importación de preguntas (CSV/JSON) y alta manual.

Reglas comunes a cualquier pregunta (manual, importada o oficial):
exactamente cuatro opciones, sin duplicados, una única respuesta correcta
entre ellas, y sin expresiones como "todas/ninguna de las anteriores".
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from typing import Any, Optional

from models.question import AREAS, DIFFICULTIES, OPTIONS, QUESTION_STATUSES, QUESTION_TYPES

FORBIDDEN_OPTION_PHRASES = (
    "todas las anteriores", "ninguna de las anteriores",
    "totes les anteriors", "cap de les anteriors",
)

LANGUAGES = ("es", "ca")

MANUAL_CSV_FIELDS = [
    "area", "topic", "subtopic", "language", "question_type", "difficulty",
    "statement", "option_a", "option_b", "option_c", "option_d", "correct_option",
    "explanation", "incorrect_explanations", "source_reference", "source_page", "legal_reference",
]

OFFICIAL_CSV_FIELDS = [
    "exam_name", "exam_year", "exam_call", "area", "topic", "language",
    "statement", "option_a", "option_b", "option_c", "option_d", "correct_option",
    "status", "source_reference", "legal_reference",
]


class ImportFormatError(Exception):
    """El archivo de importación no se puede ni siquiera leer (CSV/JSON corrupto)."""


@dataclass
class RowValidationResult:
    row_number: int
    data: dict
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def validate_question_data(data: dict, *, require_official_fields: bool = False) -> list[str]:
    """Valida los campos comunes de una pregunta. Devuelve la lista de errores (vacía si es válida)."""
    errors: list[str] = []

    statement = _clean_str(data.get("statement"))
    if not statement:
        errors.append("Falta el enunciado (statement).")

    area = _clean_str(data.get("area"))
    if not area:
        errors.append("Falta el área (area).")
    elif area not in AREAS:
        errors.append(f"Área no válida: '{area}' (debe ser 'common' o 'criminal').")

    language = _clean_str(data.get("language")) or "es"
    if language not in LANGUAGES:
        errors.append(f"Idioma no válido: '{language}' (debe ser 'es' o 'ca').")

    options = {opt: _clean_str(data.get(f"option_{opt.lower()}")) for opt in OPTIONS}
    missing_options = [opt for opt, value in options.items() if not value]
    if missing_options:
        errors.append(f"Faltan opciones: {', '.join(missing_options)}.")

    seen: dict[str, str] = {}
    for opt, value in options.items():
        if not value:
            continue
        normalized = value.lower()
        if normalized in seen:
            errors.append(f"Las opciones {seen[normalized]} y {opt} están duplicadas.")
        else:
            seen[normalized] = opt
        if any(phrase in normalized for phrase in FORBIDDEN_OPTION_PHRASES):
            errors.append(f"La opción {opt} usa una expresión no permitida (\"todas/ninguna de las anteriores\").")

    correct_option = _clean_str(data.get("correct_option")).upper()
    if not correct_option:
        errors.append("Falta la respuesta correcta (correct_option).")
    elif correct_option not in OPTIONS:
        errors.append(f"correct_option debe ser A, B, C o D (se recibió '{correct_option}').")
    elif not options.get(correct_option):
        errors.append(f"correct_option ('{correct_option}') no tiene texto en su opción correspondiente.")

    question_type = _clean_str(data.get("question_type"))
    if question_type and question_type not in QUESTION_TYPES:
        errors.append(f"question_type no válido: '{question_type}'.")

    difficulty = _clean_str(data.get("difficulty"))
    if difficulty and difficulty not in DIFFICULTIES:
        errors.append(f"difficulty no válida: '{difficulty}'.")

    if require_official_fields:
        if not _clean_str(data.get("exam_name")):
            errors.append("Falta el nombre del examen (exam_name).")
        exam_year = _clean_str(data.get("exam_year"))
        if not exam_year:
            errors.append("Falta el año del examen (exam_year).")
        elif not exam_year.isdigit():
            errors.append(f"exam_year debe ser un número (se recibió '{exam_year}').")
        status = _clean_str(data.get("status")) or "valid"
        if status not in QUESTION_STATUSES:
            errors.append(f"status no válido: '{status}' (debe ser 'valid', 'annulled' o 'reserve').")

    return errors


def build_manual_question_fields(data: dict, *, source_type: str = "manual") -> dict:
    """Normaliza los datos ya validados de una pregunta manual/importada al formato de la tabla."""
    return {
        "area": _clean_str(data.get("area")),
        "topic": _clean_str(data.get("topic")) or None,
        "subtopic": _clean_str(data.get("subtopic")) or None,
        "language": _clean_str(data.get("language")) or "es",
        "question_type": _clean_str(data.get("question_type")) or "theoretical",
        "source_type": source_type,
        "difficulty": _clean_str(data.get("difficulty")) or "intermediate",
        "statement": _clean_str(data.get("statement")),
        "option_a": _clean_str(data.get("option_a")),
        "option_b": _clean_str(data.get("option_b")),
        "option_c": _clean_str(data.get("option_c")),
        "option_d": _clean_str(data.get("option_d")),
        "correct_option": _clean_str(data.get("correct_option")).upper(),
        "explanation": _clean_str(data.get("explanation")) or None,
        "incorrect_explanations": _clean_str(data.get("incorrect_explanations")) or None,
        "source_reference": _clean_str(data.get("source_reference")) or None,
        "source_page": _clean_str(data.get("source_page")) or None,
        "legal_reference": _clean_str(data.get("legal_reference")) or None,
        "is_active": 1,
    }


def build_official_question_fields(data: dict) -> dict:
    fields = build_manual_question_fields(data, source_type="official")
    fields.update({
        "exam_name": _clean_str(data.get("exam_name")) or None,
        "exam_year": int(_clean_str(data.get("exam_year"))) if _clean_str(data.get("exam_year")).isdigit() else None,
        "exam_call": _clean_str(data.get("exam_call")) or None,
        "status": _clean_str(data.get("status")) or "valid",
    })
    return fields


def _read_text(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def parse_csv(file_bytes: bytes) -> list[dict]:
    text = _read_text(file_bytes)
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = [row for row in reader if any((v or "").strip() for v in row.values())]
    except csv.Error as exc:
        raise ImportFormatError(f"No se pudo leer el CSV: {exc}") from exc
    if reader.fieldnames is None:
        raise ImportFormatError("El CSV no tiene cabecera de columnas.")
    return rows


def parse_json(file_bytes: bytes) -> list[dict]:
    text = _read_text(file_bytes)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ImportFormatError(f"No se pudo leer el JSON: {exc}") from exc
    if isinstance(data, dict) and "questions" in data:
        data = data["questions"]
    if not isinstance(data, list):
        raise ImportFormatError("El JSON debe ser una lista de preguntas (o un objeto con la clave 'questions').")
    for item in data:
        if not isinstance(item, dict):
            raise ImportFormatError("Cada pregunta del JSON debe ser un objeto.")
    return data


def parse_import_file(filename: str, file_bytes: bytes) -> list[dict]:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "csv":
        return parse_csv(file_bytes)
    if suffix == "json":
        return parse_json(file_bytes)
    raise ImportFormatError("Solo se admiten archivos .csv o .json.")


def validate_rows(rows: list[dict], *, require_official_fields: bool = False) -> list[RowValidationResult]:
    results = []
    for index, row in enumerate(rows, start=1):
        errors = validate_question_data(row, require_official_fields=require_official_fields)
        results.append(RowValidationResult(row_number=index, data=row, errors=errors))
    return results
