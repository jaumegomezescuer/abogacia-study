"""Página Simulacro: dos partes (común y penal), cada una con su propio tiempo."""
from __future__ import annotations

import streamlit as st

from repositories import question_repository, test_repository
from services import test_service
from services.database import get_client
from services.settings_service import get_mock_exam_config
from services.translation_service import t

client = get_client()

st.title(t("nav.mock_exam"))

mock_state = test_service.get_mock_exam()


def _try_start(plan: dict) -> None:
    try:
        test_service.start_mock_exam(client, plan=plan)
    except test_service.MockExamError as exc:
        st.error(str(exc))
    else:
        st.rerun()


def _render_setup() -> None:
    tab_config, tab_custom = st.tabs([t("mock_exam.tab_current_config"), t("mock_exam.tab_custom")])

    with tab_config:
        config = get_mock_exam_config(client)
        common_total = config.common_scored_questions + config.common_reserve_questions
        criminal_total = config.criminal_scored_questions + config.criminal_reserve_questions
        st.write(t(
            "mock_exam.config_summary", common=common_total, criminal=criminal_total,
            common_minutes=config.common_time_minutes, criminal_minutes=config.criminal_time_minutes,
        ))
        show_explanations = st.checkbox(
            t("mock_exam.show_explanations_at_end"), value=True, key="mock_exam_config_explanations",
        )
        if st.button(t("mock_exam.start_button"), type="primary", key="start_config_mock_exam"):
            plan = {
                "common_count": common_total, "criminal_count": criminal_total,
                "common_time_minutes": config.common_time_minutes,
                "criminal_time_minutes": config.criminal_time_minutes,
                "correct_score": config.correct_score, "incorrect_penalty": config.incorrect_penalty,
                "blank_score": config.blank_score, "common_weight": config.common_weight,
                "criminal_weight": config.criminal_weight, "show_explanations": show_explanations,
                "source_types": None, "common_topics": None, "criminal_topics": None,
                "include_annulled": config.use_annulled_questions,
            }
            _try_start(plan)

    with tab_custom:
        col1, col2 = st.columns(2)
        with col1:
            common_count = st.number_input(
                t("mock_exam.common_count_label"), min_value=1, max_value=200, value=50,
                key="mock_custom_common_count",
            )
            common_minutes = st.number_input(
                t("mock_exam.common_minutes_label"), min_value=1, max_value=600, value=120,
                key="mock_custom_common_minutes",
            )
        with col2:
            criminal_count = st.number_input(
                t("mock_exam.criminal_count_label"), min_value=1, max_value=200, value=25,
                key="mock_custom_criminal_count",
            )
            criminal_minutes = st.number_input(
                t("mock_exam.criminal_minutes_label"), min_value=1, max_value=600, value=60,
                key="mock_custom_criminal_minutes",
            )

        col3, col4 = st.columns(2)
        with col3:
            incorrect_penalty = st.number_input(
                t("mock_exam.penalty_label"), min_value=0.0, max_value=1.0, value=1 / 3, step=0.05,
                key="mock_custom_penalty",
            )
        with col4:
            common_weight_pct = st.slider(
                t("mock_exam.common_weight_label"), min_value=0, max_value=100, value=67,
                key="mock_custom_weight",
            )

        show_explanations_custom = st.checkbox(
            t("mock_exam.show_explanations_at_end"), value=True, key="mock_exam_custom_explanations",
        )

        if st.button(t("mock_exam.start_button"), type="primary", key="start_custom_mock_exam"):
            plan = {
                "common_count": int(common_count), "criminal_count": int(criminal_count),
                "common_time_minutes": int(common_minutes), "criminal_time_minutes": int(criminal_minutes),
                "correct_score": 1.0, "incorrect_penalty": float(incorrect_penalty), "blank_score": 0.0,
                "common_weight": common_weight_pct / 100, "criminal_weight": 1 - common_weight_pct / 100,
                "show_explanations": show_explanations_custom, "source_types": None,
                "common_topics": None, "criminal_topics": None, "include_annulled": False,
            }
            _try_start(plan)


def _render_mock_question() -> None:
    question = test_service.current_question(client)
    total = test_service.total_questions()
    index = test_service.current_index()

    st.progress(index / total if total else 0.0)
    st.caption(t("study.progress_label", current=index + 1, total=total))
    st.subheader(question["statement"])

    option_labels = {opt: question[f"option_{opt.lower()}"] for opt in ("A", "B", "C", "D")}
    existing_answer = test_service.current_answer()
    options_with_blank = list(option_labels.keys()) + ["blank"]
    default_index = None
    if existing_answer:
        default_index = options_with_blank.index(
            "blank" if existing_answer["is_blank"] else existing_answer["selected_option"]
        )

    selected = st.radio(
        t("study.select_option"), options=options_with_blank,
        format_func=lambda o: t("study.leave_blank") if o == "blank" else f"{o}. {option_labels[o]}",
        key=f"mock_answer_{question['id']}", index=default_index,
    )

    def _save_current() -> None:
        if selected is not None:
            test_service.submit_answer(
                client, selected_option=(None if selected == "blank" else selected),
                is_blank=(selected == "blank"),
            )

    nav_cols = st.columns(3)
    with nav_cols[0]:
        if index > 0 and st.button(t("common.previous"), key="mock_prev"):
            _save_current()
            test_service.go_to_previous()
            st.rerun()
    with nav_cols[1]:
        next_label = t("common.next") if index < total - 1 else t("mock_exam.finish_phase_button")
        if st.button(next_label, key="mock_next", type="primary"):
            _save_current()
            test_service.go_to_next()
            st.rerun()
    with nav_cols[2]:
        if st.button(t("mock_exam.finish_phase_now_button"), key="mock_finish_now"):
            _save_current()
            test_service.jump_to_end()
            st.rerun()


def _render_exam_in_progress() -> None:
    remaining = test_service.mock_exam_time_remaining()
    if remaining is not None:
        minutes, seconds = divmod(int(remaining), 60)
        st.warning(t("mock_exam.time_remaining", minutes=minutes, seconds=seconds))
        st.caption(t("mock_exam.time_note"))
        if st.button(t("mock_exam.refresh_time_button")):
            st.rerun()

    if test_service.mock_exam_time_expired() or test_service.is_past_last_question():
        test_service.advance_mock_exam_phase(client)
        st.rerun()
        return

    st.subheader(t(f"mock_exam.phase.{mock_state['phase']}"))
    _render_mock_question()


def _render_results() -> None:
    plan = mock_state["plan"]
    common_summary = mock_state["common_summary"]
    criminal_summary = mock_state["criminal_summary"]
    score = mock_state["final_score"]

    st.success(t("mock_exam.finished_title"))

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(t("common.area.common"))
        st.metric(t("study.summary_correct"), common_summary["correct"])
        st.metric(t("study.summary_incorrect"), common_summary["incorrect"])
        st.metric(t("study.summary_blank"), common_summary["blank"])
        st.metric(t("mock_exam.part_score"), f"{score.common.normalized_0_10:.2f} / 10")
    with col2:
        st.subheader(t("common.area.criminal"))
        st.metric(t("study.summary_correct"), criminal_summary["correct"])
        st.metric(t("study.summary_incorrect"), criminal_summary["incorrect"])
        st.metric(t("study.summary_blank"), criminal_summary["blank"])
        st.metric(t("mock_exam.part_score"), f"{score.criminal.normalized_0_10:.2f} / 10")

    st.divider()
    st.metric(t("mock_exam.total_score"), f"{score.total_score_0_10:.2f} / 10")
    st.caption(t(
        "mock_exam.weight_note",
        common_weight=f"{plan['common_weight'] * 100:.0f}",
        criminal_weight=f"{plan['criminal_weight'] * 100:.0f}",
    ))

    if plan.get("show_explanations"):
        st.divider()
        st.subheader(t("mock_exam.review_title"))
        parts = ((common_summary["session_id"], t("common.area.common")),
                 (criminal_summary["session_id"], t("common.area.criminal")))
        for session_id, label in parts:
            with st.expander(label):
                answers = test_repository.list_answers_for_session(client, session_id)
                for answer in answers:
                    question = question_repository.get_by_id(client, answer["question_id"])
                    if answer["is_blank"]:
                        icon = "➖"
                    elif answer["is_correct"]:
                        icon = "✅"
                    else:
                        icon = "❌"
                    st.write(f"{icon} {question['statement']}")
                    if question.get("explanation"):
                        st.caption(question["explanation"])

    if st.button(t("mock_exam.new_mock_exam_button"), type="primary"):
        test_service.clear_mock_exam()
        st.rerun()


if mock_state is None:
    _render_setup()
elif mock_state["phase"] == "finished":
    _render_results()
else:
    _render_exam_in_progress()
