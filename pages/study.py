"""Página Estudiar: tests personalizados con modo aprendizaje o examen."""
from __future__ import annotations

import streamlit as st

from models.question import AREAS, DIFFICULTIES, QUESTION_TYPES
from repositories import document_repository, question_repository
from services import test_service
from services.database import get_client
from services.translation_service import SUPPORTED_LANGUAGES, t

client = get_client()

st.title(t("nav.study"))


def _render_filters_form() -> None:
    st.subheader(t("study.filters_title"))

    mode = st.radio(
        t("study.mode_label"), options=["learning", "exam"],
        format_func=lambda m: t(f"study.mode.{m}"), horizontal=True, key="study_mode",
    )

    col1, col2 = st.columns(2)
    with col1:
        area_choice = st.selectbox(
            t("common.area"), options=["both"] + list(AREAS),
            format_func=lambda a: t("common.area.both") if a == "both" else t(f"common.area.{a}"),
            key="study_filter_area",
        )
        areas = None if area_choice == "both" else [area_choice]

        available_topics = question_repository.distinct_topics(client, area=(areas[0] if areas else None))
        topics = st.multiselect(t("common.topic"), options=available_topics, key="study_filter_topics")

        language_choice = st.selectbox(
            t("common.language"), options=["all"] + list(SUPPORTED_LANGUAGES),
            format_func=lambda code: t("common.all") if code == "all" else t(f"common.language.{code}"),
            key="study_filter_language",
        )
        languages = None if language_choice == "all" else [language_choice]

        source_choice = st.selectbox(
            t("study.source_label"), options=["both", "official", "manual"],
            format_func=lambda s: t(f"study.source.{s}"), key="study_filter_source",
        )
        source_types = None if source_choice == "both" else [source_choice]
    with col2:
        difficulties = st.multiselect(
            t("common.difficulty"), options=list(DIFFICULTIES),
            format_func=lambda d: t(f"common.difficulty.{d}"), key="study_filter_difficulties",
        )
        question_types = st.multiselect(
            t("common.question_type"), options=list(QUESTION_TYPES),
            format_func=lambda q: t(f"common.question_type.{q}"), key="study_filter_types",
        )
        documents = document_repository.list_all(client)
        document_options = ["none"] + [doc["id"] for doc in documents]
        document_labels = {doc["id"]: doc["original_name"] for doc in documents}
        document_choice = st.selectbox(
            t("study.document_label"), options=document_options,
            format_func=lambda d: t("common.none") if d == "none" else document_labels[d],
            key="study_filter_document",
        )
        document_id = None if document_choice == "none" else document_choice

    check_col1, check_col2 = st.columns(2)
    with check_col1:
        only_never_answered = st.checkbox(t("study.only_never_answered"), key="study_filter_never")
    with check_col2:
        only_failed = st.checkbox(t("study.only_failed"), key="study_filter_failed")

    num_questions = st.number_input(
        t("study.num_questions_label"), min_value=1, max_value=200, value=10, step=1, key="study_filter_num",
    )

    if st.button(t("study.start_button"), type="primary"):
        matching = question_repository.list_questions(
            client, areas=areas, topics=(topics or None), languages=languages,
            difficulties=(difficulties or None), question_types=(question_types or None),
            source_types=source_types, document_id=document_id,
            only_never_answered=only_never_answered, only_failed=only_failed,
            order_random=True, limit=int(num_questions),
        )
        if not matching:
            st.warning(t("common.no_results"))
        else:
            test_service.start_test(
                client, question_ids=[q["id"] for q in matching], test_type="custom",
                area=(areas[0] if areas and len(areas) == 1 else None),
                language=(languages[0] if languages and len(languages) == 1 else None),
                mode=mode,
            )
            st.rerun()


def _render_feedback(question: dict, option_labels: dict, answer: dict) -> None:
    if answer["is_blank"]:
        st.info(t("study.answer_blank"))
    elif answer["is_correct"]:
        st.success(t("study.answer_correct"))
    else:
        st.error(t("study.answer_incorrect"))

    for opt, text in option_labels.items():
        if opt == question["correct_option"]:
            st.write(f"✅ **{opt}.** {text}")
        elif opt == answer["selected_option"]:
            st.write(f"❌ **{opt}.** {text}")
        else:
            st.write(f"◻️ **{opt}.** {text}")

    if question.get("explanation"):
        st.info(f"**{t('study.explanation_label')}:** {question['explanation']}")
    if question.get("incorrect_explanations"):
        st.caption(question["incorrect_explanations"])
    source_bits = [str(b) for b in (question.get("source_reference"), question.get("source_page")) if b]
    if source_bits:
        st.caption(f"{t('study.source_label')}: {' · '.join(source_bits)}")
    if question.get("legal_reference"):
        st.caption(f"{t('add_questions.legal_reference_label')}: {question['legal_reference']}")


def _render_question() -> None:
    question = test_service.current_question(client)
    total = test_service.total_questions()
    index = test_service.current_index()
    state = test_service.get_active_test()
    mode = state["mode"]

    st.progress(index / total if total else 0.0)
    st.caption(t("study.progress_label", current=index + 1, total=total))
    st.subheader(question["statement"])

    option_labels = {opt: question[f"option_{opt.lower()}"] for opt in ("A", "B", "C", "D")}
    existing_answer = test_service.current_answer()
    show_feedback = mode == "learning" and existing_answer is not None

    if show_feedback:
        _render_feedback(question, option_labels, existing_answer)
        button_label = t("study.finish_button") if index >= total - 1 else t("common.next")
        if st.button(button_label, type="primary", key=f"next_after_feedback_{question['id']}"):
            test_service.go_to_next()
            st.rerun()
    else:
        options_with_blank = list(option_labels.keys()) + ["blank"]
        default_index = None
        if existing_answer:
            default_index = options_with_blank.index("blank" if existing_answer["is_blank"] else existing_answer["selected_option"])

        selected = st.radio(
            t("study.select_option"), options=options_with_blank,
            format_func=lambda o: t("study.leave_blank") if o == "blank" else f"{o}. {option_labels[o]}",
            key=f"answer_choice_{question['id']}", index=default_index,
        )
        confidence_options = ["sure", "doubtful", "guess"]
        default_conf_index = (
            confidence_options.index(existing_answer["confidence_level"])
            if existing_answer and existing_answer["confidence_level"] in confidence_options else 0
        )
        confidence = st.radio(
            t("study.confidence_label"), options=confidence_options,
            format_func=lambda c: t(f"study.confidence.{c}"), horizontal=True,
            key=f"confidence_{question['id']}", index=default_conf_index,
        )
        marked_set = state.get("marked", set())
        mark = st.checkbox(
            t("study.mark_for_review"), value=question["id"] in marked_set, key=f"mark_{question['id']}",
        )
        if mark != (question["id"] in marked_set):
            test_service.toggle_marked(question["id"])

        if mode == "learning":
            button_label = t("study.check_answer")
        else:
            button_label = t("study.finish_button") if index >= total - 1 else t("study.save_and_next")

        if st.button(button_label, type="primary", disabled=selected is None):
            is_blank = selected == "blank"
            test_service.submit_answer(
                client, selected_option=(None if is_blank else selected),
                is_blank=is_blank, confidence_level=confidence,
            )
            if mode == "exam":
                test_service.go_to_next()
            st.rerun()

    st.divider()
    nav_cols = st.columns(2)
    with nav_cols[0]:
        if index > 0 and st.button(t("common.previous"), key="study_prev_button"):
            test_service.go_to_previous()
            st.rerun()
    with nav_cols[1]:
        if st.button(t("study.abandon_button"), key="study_abandon_button"):
            test_service.clear_active_test()
            st.rerun()


def _render_summary(summary: dict) -> None:
    st.success(t("study.test_finished"))
    cols = st.columns(4)
    cols[0].metric(t("study.summary_correct"), summary["correct"])
    cols[1].metric(t("study.summary_incorrect"), summary["incorrect"])
    cols[2].metric(t("study.summary_blank"), summary["blank"])
    cols[3].metric(t("study.summary_score"), f"{summary['score']:.2f}")

    action_cols = st.columns(2)
    with action_cols[0]:
        if st.button(t("study.new_test_button"), type="primary"):
            test_service.clear_active_test()
            st.rerun()
    with action_cols[1]:
        if st.button(t("home.review_errors_button")):
            test_service.clear_active_test()
            st.switch_page("pages/errors.py")


_state = test_service.get_active_test()
if _state is None:
    _render_filters_form()
elif _state.get("finished"):
    _render_summary(_state["summary"])
elif test_service.is_past_last_question():
    _render_summary(test_service.finish_test(client))
else:
    _render_question()
