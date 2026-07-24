"""Pruebas de humo: arrancan la app real (vía AppTest) y comprueban que no
haya excepciones no controladas. Usan .streamlit/secrets.toml del entorno
de desarrollo local (base de datos SQLite de archivo, no Turso remoto).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

pytestmark = pytest.mark.skipif(
    not (Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml").exists(),
    reason="Requiere .streamlit/secrets.toml local para las pruebas de humo",
)


def test_login_gate_blocks_without_password():
    at = AppTest.from_file("app.py")
    at.run()
    assert not at.exception
    titles = [el.value for el in at.title]
    assert titles  # se muestra la pantalla de login, no el contenido protegido


def test_home_page_renders_after_login():
    at = AppTest.from_file("app.py")
    at.session_state["authenticated"] = True
    at.run()
    assert not at.exception


def test_wrong_password_is_rejected():
    at = AppTest.from_file("app.py")
    at.run()
    text_inputs = [w for w in at.text_input]
    assert text_inputs, "No se encontró el campo de contraseña"
    text_inputs[0].set_value("contraseña-incorrecta")
    submit_buttons = [b for b in at.button]
    assert submit_buttons, "No se encontró el botón de acceso"
    submit_buttons[0].click().run()
    assert not at.exception
    assert ("authenticated" not in at.session_state) or at.session_state["authenticated"] is not True
    error_texts = [el.value for el in at.error]
    assert error_texts  # se muestra un mensaje de error


def test_correct_password_grants_access():
    at = AppTest.from_file("app.py")
    at.run()
    text_inputs = [w for w in at.text_input]
    text_inputs[0].set_value("dev-local-test")  # coincide con .streamlit/secrets.toml de desarrollo
    submit_buttons = [b for b in at.button]
    submit_buttons[0].click().run()
    assert not at.exception
    assert at.session_state["authenticated"] is True


def test_language_switch_changes_interface_text():
    at = AppTest.from_file("app.py")
    at.session_state["authenticated"] = True
    at.run()
    assert not at.exception

    es_titles = [el.value for el in at.title]
    assert any("Inicio" in title for title in es_titles)

    at.selectbox(key="language_selector").set_value("ca")
    at.run()
    assert not at.exception
    assert at.session_state["language"] == "ca"

    # El título de la página, ya renderizado dentro de la sesión de AppTest,
    # debe reflejar el nuevo idioma ("Inici" en catalán, sección nav.home).
    ca_titles = [el.value for el in at.title]
    assert any(title == "Inici" for title in ca_titles)
    assert not any(title == "Inicio" for title in ca_titles)


def test_material_page_renders_with_a_document():
    from services.database import create_test_client
    from repositories import document_repository

    setup_client = create_test_client("data/dev_local.db")
    document_repository.create(
        setup_client, original_name="smoke_test.txt", stored_name="smoke_test.txt",
        file_type="txt", file_content=b"contenido de prueba", area="common",
        topic="Tema de prueba", material_type="notes", language="es", page_count=None,
        text_content="Contenido de prueba extraído.", processing_status="processed",
        processing_error=None,
    )
    setup_client.close()

    at = AppTest.from_file("app.py")
    at.session_state["authenticated"] = True
    at.run()
    at.switch_page("pages/material.py")
    at.run()
    assert not at.exception


def test_add_questions_page_renders():
    at = AppTest.from_file("app.py")
    at.session_state["authenticated"] = True
    at.run()
    at.switch_page("pages/add_questions.py")
    at.run()
    assert not at.exception


def _seed_questions_for_study_flow():
    from services.database import create_test_client
    from repositories import question_repository

    setup_client = create_test_client("data/dev_local.db")
    ids = question_repository.bulk_create(setup_client, [
        {
            "area": "common", "topic": "__smoke_study_topic__", "language": "es",
            "question_type": "theoretical", "source_type": "manual", "difficulty": "basic",
            "statement": "Pregunta de humo 1. Ejemplo técnico.",
            "option_a": "A1", "option_b": "B1", "option_c": "C1", "option_d": "D1",
            "correct_option": "A", "explanation": "Explicación de humo 1.",
        },
        {
            "area": "common", "topic": "__smoke_study_topic__", "language": "es",
            "question_type": "theoretical", "source_type": "manual", "difficulty": "basic",
            "statement": "Pregunta de humo 2. Ejemplo técnico.",
            "option_a": "A2", "option_b": "B2", "option_c": "C2", "option_d": "D2",
            "correct_option": "B", "explanation": "Explicación de humo 2.",
        },
    ])
    setup_client.close()
    return ids


def test_study_filters_form_renders():
    _seed_questions_for_study_flow()
    at = AppTest.from_file("app.py")
    at.session_state["authenticated"] = True
    at.run()
    at.switch_page("pages/study.py")
    at.run()
    assert not at.exception


def test_full_study_flow_learning_mode_to_summary():
    ids = _seed_questions_for_study_flow()

    at = AppTest.from_file("app.py")
    at.session_state["authenticated"] = True
    at.run()
    at.switch_page("pages/study.py")
    at.run()
    assert not at.exception

    at.multiselect(key="study_filter_topics").set_value(["__smoke_study_topic__"])
    at.number_input(key="study_filter_num").set_value(2)
    at.run()

    # st.button no admite `key` como filtro de búsqueda en AppTest; se busca por su etiqueta traducida.
    from services.translation_service import t as translate
    start_label = translate("study.start_button")
    matching = [b for b in at.button if b.label == start_label]
    assert matching, "No se encontró el botón de inicio del test"
    matching[0].click().run()
    assert not at.exception

    # Debe mostrarse la primera pregunta (ya no el formulario de filtros).
    assert at.session_state["active_test"] is not None
    assert at.session_state["active_test"]["current_index"] == 0

    for _ in range(2):
        question_id = at.session_state["active_test"]["question_ids"][at.session_state["active_test"]["current_index"]]
        at.radio(key=f"answer_choice_{question_id}").set_value("A")
        at.run()
        check_label = translate("study.check_answer")
        check_buttons = [b for b in at.button if b.label == check_label]
        assert check_buttons
        check_buttons[0].click().run()
        assert not at.exception

        next_label = translate("common.next")
        finish_label = translate("study.finish_button")
        next_buttons = [b for b in at.button if b.label in (next_label, finish_label)]
        assert next_buttons
        next_buttons[0].click().run()
        assert not at.exception

    assert at.session_state["active_test"]["finished"] is True
    summary_texts = [el.value for el in at.success]
    assert any(translate("study.test_finished") in text for text in summary_texts)


def test_full_mock_exam_flow_to_results():
    from services.database import create_test_client
    from repositories import question_repository

    setup_client = create_test_client("data/dev_local.db")
    for area, letter in (("common", "A"), ("criminal", "B")):
        question_repository.create(setup_client, {
            "area": area, "topic": "__smoke_mock_exam__", "language": "es",
            "question_type": "theoretical", "source_type": "manual", "difficulty": "basic",
            "statement": f"Pregunta de humo simulacro ({area}). Ejemplo técnico.",
            "option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D",
            "correct_option": letter,
        })
    setup_client.close()

    at = AppTest.from_file("app.py")
    at.session_state["authenticated"] = True
    at.run()
    at.switch_page("pages/mock_exam.py")
    at.run()
    assert not at.exception

    at.number_input(key="mock_custom_common_count").set_value(1)
    at.number_input(key="mock_custom_criminal_count").set_value(1)
    at.run()
    at.button(key="start_custom_mock_exam").click().run()
    assert not at.exception
    assert at.session_state["mock_exam"]["phase"] == "common"

    at.button(key="mock_finish_now").click().run()
    assert not at.exception
    assert at.session_state["mock_exam"]["phase"] == "criminal"

    at.button(key="mock_finish_now").click().run()
    assert not at.exception
    assert at.session_state["mock_exam"]["phase"] == "finished"

    from services.translation_service import t as translate
    success_texts = [el.value for el in at.success]
    assert any(translate("mock_exam.finished_title") in text for text in success_texts)


def test_official_questions_page_renders():
    from services.database import create_test_client
    from repositories import question_repository

    setup_client = create_test_client("data/dev_local.db")
    question_repository.create(setup_client, {
        "area": "common", "topic": "__smoke_official__", "language": "es",
        "question_type": "theoretical", "source_type": "official", "difficulty": "basic",
        "statement": "Pregunta oficial de humo. Ejemplo técnico.",
        "option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D",
        "correct_option": "A", "exam_name": "Examen de humo", "exam_year": 2024,
        "exam_call": "Convocatoria de humo", "status": "valid",
    })
    setup_client.close()

    at = AppTest.from_file("app.py")
    at.session_state["authenticated"] = True
    at.run()
    at.switch_page("pages/official_questions.py")
    at.run()
    assert not at.exception


def test_statistics_page_renders_with_and_without_data():
    at = AppTest.from_file("app.py")
    at.session_state["authenticated"] = True
    at.run()
    at.switch_page("pages/statistics.py")
    at.run()
    assert not at.exception

    _seed_questions_for_study_flow()
    at2 = AppTest.from_file("app.py")
    at2.session_state["authenticated"] = True
    at2.run()
    at2.switch_page("pages/study.py")
    at2.run()
    from services.translation_service import t as translate
    matching = [b for b in at2.button if b.label == translate("study.start_button")]
    matching[0].click().run()
    while "active_test" in at2.session_state and not at2.session_state["active_test"]["finished"]:
        q_ids = at2.session_state["active_test"]["question_ids"]
        idx = at2.session_state["active_test"]["current_index"]
        question_id = q_ids[idx]
        at2.radio(key=f"answer_choice_{question_id}").set_value("A")
        at2.run()
        check_buttons = [b for b in at2.button if b.label == translate("study.check_answer")]
        check_buttons[0].click().run()
        next_buttons = [
            b for b in at2.button
            if b.label in (translate("common.next"), translate("study.finish_button"))
        ]
        next_buttons[0].click().run()
    assert not at2.exception

    at3 = AppTest.from_file("app.py")
    at3.session_state["authenticated"] = True
    at3.run()
    at3.switch_page("pages/statistics.py")
    at3.run()
    assert not at3.exception


def test_settings_page_renders_and_saves_config():
    at = AppTest.from_file("app.py")
    at.session_state["authenticated"] = True
    at.run()
    at.switch_page("pages/settings.py")
    at.run()
    assert not at.exception

    at.button(key="save_mock_exam_config").click().run()
    assert not at.exception
