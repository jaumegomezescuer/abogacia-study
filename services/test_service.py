"""Gestión de la sesión de test en curso (`st.session_state`) y su guardado.

Se usa tanto desde "Estudiar" (tests personalizados y repaso de errores)
como desde el simulacro. El estado en memoria se guarda bajo una única
clave (`SESSION_KEY`) para no perder el test con interacciones sueltas ni
duplicar sesiones guardadas en la base de datos.
"""
from __future__ import annotations

import time
from typing import Optional

import streamlit as st

from repositories import question_repository, test_repository
from services.scoring_service import calculate_score
from services.settings_service import get_mock_exam_config

SESSION_KEY = "active_test"


def start_test(client, *, question_ids: list[int], test_type: str,
                area: Optional[str] = None, language: Optional[str] = None,
                mode: str = "learning") -> None:
    if not question_ids:
        raise ValueError("No hay preguntas disponibles para iniciar el test.")
    session_id = test_repository.create_session(
        client, test_type=test_type, area=area, language=language,
        total_questions=len(question_ids),
    )
    st.session_state[SESSION_KEY] = {
        "session_id": session_id,
        "test_type": test_type,
        "mode": mode,
        "question_ids": list(question_ids),
        "current_index": 0,
        "answers": {},
        "marked": set(),
        "question_start_time": time.time(),
        "started_at": time.time(),
        "finished": False,
        "summary": None,
    }


def has_active_test() -> bool:
    state = st.session_state.get(SESSION_KEY)
    return bool(state) and not state.get("finished", False)


def get_active_test() -> Optional[dict]:
    return st.session_state.get(SESSION_KEY)


def clear_active_test() -> None:
    st.session_state.pop(SESSION_KEY, None)


def total_questions() -> int:
    state = get_active_test()
    return len(state["question_ids"]) if state else 0


def current_index() -> int:
    state = get_active_test()
    return state["current_index"] if state else 0


def current_question(client) -> Optional[dict]:
    state = get_active_test()
    if not state or state["current_index"] >= len(state["question_ids"]):
        return None
    question_id = state["question_ids"][state["current_index"]]
    return question_repository.get_by_id(client, question_id)


def current_answer() -> Optional[dict]:
    state = get_active_test()
    if not state:
        return None
    question_id = state["question_ids"][state["current_index"]]
    return state["answers"].get(question_id)


def submit_answer(client, *, selected_option: Optional[str], is_blank: bool,
                   confidence_level: str = "not_set") -> None:
    state = get_active_test()
    if not state:
        return
    question_id = state["question_ids"][state["current_index"]]
    question = question_repository.get_by_id(client, question_id)
    is_correct = None if is_blank else (selected_option == question["correct_option"])
    elapsed = time.time() - state["question_start_time"]
    state["answers"][question_id] = {
        "selected_option": selected_option,
        "is_blank": is_blank,
        "is_correct": is_correct,
        "confidence_level": confidence_level,
        "response_time_seconds": round(elapsed, 1),
    }


def toggle_marked(question_id: int) -> None:
    state = get_active_test()
    if not state:
        return
    marked = state.setdefault("marked", set())
    if question_id in marked:
        marked.discard(question_id)
    else:
        marked.add(question_id)


def go_to(index: int) -> None:
    state = get_active_test()
    if not state:
        return
    state["current_index"] = max(0, min(index, len(state["question_ids"]) - 1))
    state["question_start_time"] = time.time()


def go_to_next() -> None:
    state = get_active_test()
    if not state:
        return
    state["current_index"] += 1
    state["question_start_time"] = time.time()


def go_to_previous() -> None:
    go_to(current_index() - 1)


def is_past_last_question() -> bool:
    state = get_active_test()
    if not state:
        return True
    return state["current_index"] >= len(state["question_ids"])


def jump_to_end() -> None:
    """Fuerza el final del test actual (usado para 'finalizar esta parte ahora')."""
    state = get_active_test()
    if state:
        state["current_index"] = len(state["question_ids"])


def finish_test(client) -> dict:
    """Guarda todas las respuestas y el progreso, y calcula la puntuación."""
    state = get_active_test()
    if not state:
        raise ValueError("No hay ningún test activo.")

    config = get_mock_exam_config(client)
    correct = incorrect = blank = 0
    for question_id in state["question_ids"]:
        answer = state["answers"].get(question_id) or {
            "selected_option": None, "is_blank": True, "is_correct": None,
            "confidence_level": "not_set", "response_time_seconds": None,
        }
        test_repository.create_answer(
            client, test_session_id=state["session_id"], question_id=question_id,
            selected_option=answer["selected_option"], is_correct=answer["is_correct"],
            is_blank=answer["is_blank"], confidence_level=answer["confidence_level"],
            response_time_seconds=answer["response_time_seconds"],
        )
        if answer["is_blank"]:
            blank += 1
            result = "blank"
        elif answer["is_correct"]:
            correct += 1
            result = "correct"
        else:
            incorrect += 1
            result = "incorrect"
        test_repository.record_answer_progress(client, question_id, result=result)

    score = calculate_score(
        correct=correct, incorrect=incorrect, blank=blank,
        correct_score=config.correct_score, incorrect_penalty=config.incorrect_penalty,
        blank_score=config.blank_score,
    )
    duration = int(time.time() - state["started_at"])
    test_repository.finish_session(
        client, state["session_id"], total_questions=len(state["question_ids"]),
        correct_answers=correct, incorrect_answers=incorrect, blank_answers=blank,
        raw_score=score, penalized_score=score, duration_seconds=duration,
    )
    summary = {
        "session_id": state["session_id"], "correct": correct, "incorrect": incorrect,
        "blank": blank, "total": len(state["question_ids"]), "score": score,
        "duration_seconds": duration,
    }
    state["finished"] = True
    state["summary"] = summary
    return summary


def start_quick_test(client, *, num_questions: int = 10) -> bool:
    """Inicia un test rápido con preguntas activas aleatorias. Devuelve si pudo iniciarse."""
    question_ids = [
        row["id"] for row in question_repository.list_questions(
            client, order_random=True, limit=num_questions,
        )
    ]
    if not question_ids:
        return False
    start_test(client, question_ids=question_ids, test_type="practice", mode="learning")
    return True


# --- Simulacro (dos partes: común y penal, cada una con su propio límite de tiempo) ---

MOCK_EXAM_KEY = "mock_exam"


class MockExamError(Exception):
    pass


def start_mock_exam(client, *, plan: dict) -> None:
    """Elige las preguntas de ambas partes (comprobando que hay suficientes) y arranca la primera."""
    exclude_annulled = not plan.get("include_annulled", False)
    common_ids = [
        row["id"] for row in question_repository.list_questions(
            client, areas=["common"], source_types=plan.get("source_types"),
            topics=(plan.get("common_topics") or None), exclude_annulled=exclude_annulled,
            order_random=True, limit=plan["common_count"],
        )
    ]
    criminal_ids = [
        row["id"] for row in question_repository.list_questions(
            client, areas=["criminal"], source_types=plan.get("source_types"),
            topics=(plan.get("criminal_topics") or None), exclude_annulled=exclude_annulled,
            order_random=True, limit=plan["criminal_count"],
        )
    ]
    if len(common_ids) < plan["common_count"] or len(criminal_ids) < plan["criminal_count"]:
        raise MockExamError(
            "No hay preguntas suficientes para el simulacro configurado: "
            f"parte común {len(common_ids)}/{plan['common_count']}, "
            f"parte penal {len(criminal_ids)}/{plan['criminal_count']}."
        )

    st.session_state[MOCK_EXAM_KEY] = {
        "plan": plan,
        "phase": "common",
        "common_summary": None,
        "criminal_summary": None,
        "final_score": None,
        "criminal_question_ids": criminal_ids,
    }
    start_test(client, question_ids=common_ids, test_type="mock_exam", area="common", mode="exam")
    get_active_test()["time_limit_seconds"] = plan["common_time_minutes"] * 60


def get_mock_exam() -> Optional[dict]:
    return st.session_state.get(MOCK_EXAM_KEY)


def clear_mock_exam() -> None:
    st.session_state.pop(MOCK_EXAM_KEY, None)
    clear_active_test()


def mock_exam_time_remaining() -> Optional[float]:
    state = get_active_test()
    if not state or "time_limit_seconds" not in state:
        return None
    elapsed = time.time() - state["started_at"]
    return max(0.0, state["time_limit_seconds"] - elapsed)


def mock_exam_time_expired() -> bool:
    remaining = mock_exam_time_remaining()
    return remaining is not None and remaining <= 0


def advance_mock_exam_phase(client) -> dict:
    """Guarda la parte actual y arranca la siguiente, o calcula la nota final si ya era la última."""
    mock_state = get_mock_exam()
    if not mock_state:
        raise MockExamError("No hay ningún simulacro activo.")

    summary = finish_test(client)
    plan = mock_state["plan"]

    if mock_state["phase"] == "common":
        mock_state["common_summary"] = summary
        mock_state["phase"] = "criminal"
        start_test(
            client, question_ids=mock_state["criminal_question_ids"],
            test_type="mock_exam", area="criminal", mode="exam",
        )
        get_active_test()["time_limit_seconds"] = plan["criminal_time_minutes"] * 60
    else:
        mock_state["criminal_summary"] = summary
        mock_state["phase"] = "finished"
        from services.scoring_service import calculate_mock_exam_score
        common_summary = mock_state["common_summary"]
        mock_state["final_score"] = calculate_mock_exam_score(
            common_correct=common_summary["correct"], common_incorrect=common_summary["incorrect"],
            common_blank=common_summary["blank"], criminal_correct=summary["correct"],
            criminal_incorrect=summary["incorrect"], criminal_blank=summary["blank"],
            correct_score=plan["correct_score"], incorrect_penalty=plan["incorrect_penalty"],
            blank_score=plan["blank_score"], common_weight=plan["common_weight"],
            criminal_weight=plan["criminal_weight"],
        )
        clear_active_test()
    return mock_state
