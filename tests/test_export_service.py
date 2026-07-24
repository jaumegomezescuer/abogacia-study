import csv
import io
import json

from repositories import document_repository, question_repository, test_repository
from services import export_service


def _seed_one_question(db_client) -> int:
    return question_repository.create(db_client, {
        "area": "common", "topic": "Tema export", "language": "es",
        "question_type": "theoretical", "source_type": "manual", "difficulty": "basic",
        "statement": "Pregunta de exportación.", "option_a": "A", "option_b": "B",
        "option_c": "C", "option_d": "D", "correct_option": "A",
    })


def test_export_questions_csv_roundtrips_headers(db_client):
    _seed_one_question(db_client)
    csv_bytes = export_service.export_questions_csv(db_client)
    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig")))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["statement"] == "Pregunta de exportación."
    assert rows[0]["correct_option"] == "A"


def test_export_questions_json_contains_question(db_client):
    _seed_one_question(db_client)
    payload = json.loads(export_service.export_questions_json(db_client))
    assert len(payload) == 1
    assert payload[0]["area"] == "common"


def test_export_full_database_includes_all_tables(db_client):
    document_repository.create(
        db_client, original_name="a.txt", stored_name="a.txt", file_type="txt",
        file_content=b"contenido", area="common", topic=None, material_type="notes",
        language="es", page_count=None, text_content="contenido", processing_status="processed",
        processing_error=None,
    )
    _seed_one_question(db_client)
    payload = json.loads(export_service.export_full_database_json(db_client))
    assert len(payload["documents"]) == 1
    assert payload["documents"][0]["file_content_base64"]
    assert "file_content" not in payload["documents"][0]
    assert len(payload["questions"]) == 1
    assert "test_sessions" in payload and "test_answers" in payload and "question_progress" in payload


def test_delete_all_data_empties_every_table(db_client):
    document_repository.create(
        db_client, original_name="a.txt", stored_name="a.txt", file_type="txt",
        file_content=b"x", area="common", topic=None, material_type="notes",
        language="es", page_count=None, text_content="x", processing_status="processed",
        processing_error=None,
    )
    question_id = _seed_one_question(db_client)
    session_id = test_repository.create_session(db_client, test_type="practice", area="common", language="es")
    test_repository.create_answer(
        db_client, test_session_id=session_id, question_id=question_id, selected_option="A",
        is_correct=True, is_blank=False, confidence_level="sure", response_time_seconds=1.0,
    )
    test_repository.record_answer_progress(db_client, question_id, result="correct")

    export_service.delete_all_data(db_client)

    assert document_repository.count(db_client) == 0
    assert question_repository.count(db_client, is_active=None) == 0
    assert test_repository.list_sessions(db_client, only_completed=False) == []
    # Las tablas deben seguir existiendo y ser usables tras el borrado.
    new_id = _seed_one_question(db_client)
    assert question_repository.get_by_id(db_client, new_id) is not None
