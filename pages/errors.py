"""Página de Errores: cuaderno de preguntas falladas y su repaso."""
from __future__ import annotations

import streamlit as st

from models.question import AREAS
from repositories import question_repository, test_repository
from services import test_service
from services.database import get_client
from services.translation_service import t

client = get_client()

st.title(t("nav.errors"))

col1, col2 = st.columns(2)
with col1:
    area_choice = st.selectbox(
        t("common.area"), options=["both"] + list(AREAS),
        format_func=lambda a: t("common.area.both") if a == "both" else t(f"common.area.{a}"),
        key="errors_filter_area",
    )
    areas = None if area_choice == "both" else [area_choice]
    available_topics = question_repository.distinct_topics(client, area=(areas[0] if areas else None))
    topics = st.multiselect(t("common.topic"), options=available_topics, key="errors_filter_topics")
with col2:
    only_multiple_failures = st.checkbox(t("errors.only_multiple_failures"), key="errors_filter_multiple")
    only_marked = st.checkbox(t("errors.only_marked"), key="errors_filter_marked")

failed_questions = question_repository.list_with_progress(
    client, areas=areas, topics=(topics or None),
    only_multiple_failures=only_multiple_failures, only_marked=only_marked,
)

st.caption(t("errors.count_summary", count=len(failed_questions)))

if failed_questions:
    if st.button(t("errors.review_all_button"), type="primary"):
        test_service.start_test(
            client, question_ids=[q["id"] for q in failed_questions], test_type="error_review",
            area=(areas[0] if areas and len(areas) == 1 else None), mode="learning",
        )
        st.switch_page("pages/study.py")

st.divider()

if not failed_questions:
    st.caption(t("common.no_results"))

for question in failed_questions:
    area_label = t(f"common.area.{question['area']}")
    marked_icon = "🔖 " if question["marked_for_review"] else ""
    header = f"{marked_icon}{question['statement'][:90]}"
    with st.expander(header):
        info_cols = st.columns(4)
        info_cols[0].write(f"**{t('common.area')}:** {area_label}")
        info_cols[1].write(f"**{t('common.topic')}:** {question['topic'] or '—'}")
        info_cols[2].write(f"**{t('errors.times_seen')}:** {question['times_seen']}")
        info_cols[3].write(f"**{t('errors.times_incorrect')}:** {question['times_incorrect']}")

        last_answered = (question["last_answered_at"] or "")[:16].replace("T", " ")
        st.caption(f"{t('errors.last_answered_at')}: {last_answered or '—'}")

        option_labels = {opt: question[f"option_{opt.lower()}"] for opt in ("A", "B", "C", "D")}
        for opt, text in option_labels.items():
            prefix = "✅" if opt == question["correct_option"] else "◻️"
            st.write(f"{prefix} **{opt}.** {text}")
        if question.get("explanation"):
            st.info(f"**{t('study.explanation_label')}:** {question['explanation']}")
        if question.get("legal_reference"):
            st.caption(f"{t('add_questions.legal_reference_label')}: {question['legal_reference']}")

        action_cols = st.columns(3)
        with action_cols[0]:
            if st.button(t("errors.mark_mastered"), key=f"mastered_{question['id']}"):
                test_repository.mark_as_mastered(client, question["id"])
                st.rerun()
        with action_cols[1]:
            if st.button(t("errors.reset_progress"), key=f"reset_{question['id']}"):
                test_repository.reset_question_progress(client, question["id"])
                st.rerun()
        with action_cols[2]:
            if st.button(t("study.start_button"), key=f"review_one_{question['id']}"):
                test_service.start_test(
                    client, question_ids=[question["id"]], test_type="error_review", mode="learning",
                )
                st.switch_page("pages/study.py")
