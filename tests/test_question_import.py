import pytest

from repositories import question_repository
from services.question_service import (
    ImportFormatError,
    RowValidationResult,
    build_manual_question_fields,
    parse_csv,
    parse_json,
    validate_question_data,
    validate_rows,
)

VALID_QUESTION = {
    "area": "common", "topic": "Tema 1", "language": "es",
    "question_type": "theoretical", "difficulty": "basic",
    "statement": "Pregunta de ejemplo técnico. No corresponde a contenido jurídico real.",
    "option_a": "Opción A", "option_b": "Opción B",
    "option_c": "Opción C", "option_d": "Opción D",
    "correct_option": "B", "explanation": "Explicación de ejemplo.",
}


def test_valid_question_has_no_errors():
    assert validate_question_data(VALID_QUESTION) == []


def test_requires_four_options():
    data = dict(VALID_QUESTION, option_d="")
    errors = validate_question_data(data)
    assert any("Faltan opciones" in e for e in errors)


def test_correct_option_must_be_a_valid_letter():
    data = dict(VALID_QUESTION, correct_option="E")
    errors = validate_question_data(data)
    assert any("correct_option" in e for e in errors)


def test_correct_option_must_have_text():
    data = dict(VALID_QUESTION, correct_option="B", option_b="")
    errors = validate_question_data(data)
    assert any("Faltan opciones" in e or "correct_option" in e for e in errors)


def test_rejects_duplicate_options():
    data = dict(VALID_QUESTION, option_c="Opción A")
    errors = validate_question_data(data)
    assert any("duplicadas" in e for e in errors)


def test_rejects_forbidden_all_of_the_above():
    data = dict(VALID_QUESTION, option_d="Todas las anteriores")
    errors = validate_question_data(data)
    assert any("no permitida" in e for e in errors)


def test_rejects_invalid_area():
    data = dict(VALID_QUESTION, area="civil")
    errors = validate_question_data(data)
    assert any("Área no válida" in e for e in errors)


def test_official_question_requires_exam_metadata():
    data = dict(VALID_QUESTION)
    errors = validate_question_data(data, require_official_fields=True)
    assert any("exam_name" in e for e in errors)
    assert any("exam_year" in e for e in errors)


def test_parse_csv_valid_file():
    csv_bytes = (
        "area,topic,language,question_type,difficulty,statement,"
        "option_a,option_b,option_c,option_d,correct_option,explanation\n"
        "common,Tema 1,es,theoretical,basic,Pregunta de ejemplo técnico,"
        "A,B,C,D,A,Explicación\n"
    ).encode("utf-8")
    rows = parse_csv(csv_bytes)
    assert len(rows) == 1
    assert rows[0]["area"] == "common"


def test_parse_csv_without_header_raises():
    with pytest.raises(ImportFormatError):
        parse_csv(b"")


def test_parse_json_valid_list():
    import json
    payload = json.dumps([VALID_QUESTION]).encode("utf-8")
    rows = parse_json(payload)
    assert len(rows) == 1
    assert rows[0]["statement"] == VALID_QUESTION["statement"]


def test_parse_json_invalid_raises():
    with pytest.raises(ImportFormatError):
        parse_json(b"{not valid json")


def test_validate_rows_reports_row_number_and_reason():
    rows = [VALID_QUESTION, dict(VALID_QUESTION, option_a="")]
    results = validate_rows(rows)
    assert results[0].is_valid
    assert not results[1].is_valid
    assert results[1].row_number == 2
    assert results[1].errors


def test_import_valid_rows_into_repository(db_client):
    results = validate_rows([VALID_QUESTION])
    valid_fields = [build_manual_question_fields(r.data) for r in results if r.is_valid]
    ids = question_repository.bulk_create(db_client, valid_fields)
    assert len(ids) == 1
    saved = question_repository.get_by_id(db_client, ids[0])
    assert saved["source_type"] == "manual"
    assert saved["correct_option"] == "B"
