from repositories import document_repository, question_repository, test_repository


def test_tables_are_created(db_client):
    tables = {
        row[0]
        for row in db_client.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).rows
    }
    expected = {
        "documents", "questions", "test_sessions", "test_answers",
        "question_progress", "app_settings", "schema_migrations",
    }
    assert expected.issubset(tables)


def test_running_migrations_twice_is_safe(db_client):
    from services.database import run_migrations
    run_migrations(db_client)  # ya se ejecutó al crear el cliente de prueba
    run_migrations(db_client)  # no debe fallar ni duplicar nada
    count = db_client.execute("SELECT COUNT(*) FROM schema_migrations").rows[0][0]
    assert count == 1


def test_insert_document(db_client):
    doc_id = document_repository.create(
        db_client, original_name="apuntes.pdf", stored_name="apuntes.pdf",
        file_type="pdf", file_content=b"%PDF-1.4 contenido", area="common",
        topic="Tema 1", material_type="notes", language="es", page_count=3,
        text_content="texto extraído", processing_status="processed", processing_error=None,
    )
    assert doc_id > 0
    doc = document_repository.get_by_id(db_client, doc_id, include_content=True)
    assert doc["original_name"] == "apuntes.pdf"
    assert doc["file_content"] == b"%PDF-1.4 contenido"
    assert document_repository.count(db_client) == 1


def test_insert_question(db_client):
    question_id = question_repository.create(db_client, {
        "area": "criminal", "topic": "Tema 4", "language": "es",
        "question_type": "theoretical", "source_type": "manual", "difficulty": "basic",
        "statement": "Pregunta de ejemplo técnico.",
        "option_a": "Opción A", "option_b": "Opción B",
        "option_c": "Opción C", "option_d": "Opción D",
        "correct_option": "A", "explanation": "Explicación de ejemplo.",
    })
    assert question_id > 0
    question = question_repository.get_by_id(db_client, question_id)
    assert question["area"] == "criminal"
    assert question["source_type"] == "manual"
    assert question["is_active"] == 1


def test_delete_document_with_binary_content(db_client):
    binary_content = bytes(range(256)) * 100  # contenido binario no trivial
    doc_id = document_repository.create(
        db_client, original_name="apuntes.pdf", stored_name="apuntes.pdf", file_type="pdf",
        file_content=binary_content, area="common", topic="Tema 1", material_type="notes",
        language="es", page_count=5, text_content="texto", processing_status="processed",
        processing_error=None,
    )
    stored = document_repository.get_by_id(db_client, doc_id, include_content=True)
    assert stored["file_content"] == binary_content

    document_repository.delete(db_client, doc_id)

    assert document_repository.get_by_id(db_client, doc_id) is None
    assert document_repository.count(db_client) == 0


def test_delete_document_keeps_questions_by_default(db_client):
    doc_id = document_repository.create(
        db_client, original_name="a.pdf", stored_name="a.pdf", file_type="pdf",
        file_content=None, area="common", topic="Tema 1", material_type="notes",
        language="es", page_count=None, text_content=None,
        processing_status="processed", processing_error=None,
    )
    question_id = question_repository.create(db_client, {
        "document_id": doc_id, "area": "common", "language": "es",
        "question_type": "theoretical", "source_type": "manual", "difficulty": "basic",
        "statement": "Pregunta ligada a un documento.",
        "option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D",
        "correct_option": "B",
    })
    affected = document_repository.delete(db_client, doc_id, keep_questions=True)
    assert affected == 1
    assert document_repository.get_by_id(db_client, doc_id) is None
    question = question_repository.get_by_id(db_client, question_id)
    assert question is not None
    assert question["document_id"] is None


def test_delete_document_can_remove_linked_questions(db_client):
    doc_id = document_repository.create(
        db_client, original_name="a.pdf", stored_name="a.pdf", file_type="pdf",
        file_content=None, area="common", topic=None, material_type="notes",
        language="es", page_count=None, text_content=None,
        processing_status="processed", processing_error=None,
    )
    question_id = question_repository.create(db_client, {
        "document_id": doc_id, "area": "common", "language": "es",
        "question_type": "theoretical", "source_type": "manual", "difficulty": "basic",
        "statement": "Pregunta ligada.",
        "option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D",
        "correct_option": "C",
    })
    document_repository.delete(db_client, doc_id, keep_questions=False)
    assert question_repository.get_by_id(db_client, question_id) is None


def test_record_answer_and_progress(db_client):
    question_id = question_repository.create(db_client, {
        "area": "common", "language": "es", "question_type": "theoretical",
        "source_type": "manual", "difficulty": "basic",
        "statement": "Pregunta.", "option_a": "A", "option_b": "B",
        "option_c": "C", "option_d": "D", "correct_option": "D",
    })
    session_id = test_repository.create_session(db_client, test_type="practice", area="common", language="es")
    test_repository.create_answer(
        db_client, test_session_id=session_id, question_id=question_id,
        selected_option="A", is_correct=False, is_blank=False,
        confidence_level="guess", response_time_seconds=12.5,
    )
    test_repository.record_answer_progress(db_client, question_id, result="incorrect")

    answers = test_repository.list_answers_for_session(db_client, session_id)
    assert len(answers) == 1
    assert answers[0]["is_correct"] == 0

    progress = test_repository.get_question_progress(db_client, question_id)
    assert progress["times_seen"] == 1
    assert progress["times_incorrect"] == 1
