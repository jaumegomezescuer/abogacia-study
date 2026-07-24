"""Página de Inicio: resumen del progreso de estudio."""
from __future__ import annotations

import streamlit as st

from repositories import document_repository, question_repository, test_repository
from services import test_service
from services.database import get_client
from services.translation_service import t

client = get_client()

st.title(t("nav.home"))
st.caption(t("home.welcome"))

total_questions = question_repository.count(client)
document_count = document_repository.count(client)

if total_questions == 0 and document_count == 0:
    st.info(t("home.empty_title"))
    st.write(t("home.empty_step1"))
    st.write(t("home.empty_step2"))
    st.write(t("home.empty_step3"))
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t("home.go_to_material"), use_container_width=True):
            st.switch_page("pages/material.py")
    with col2:
        if st.button(t("home.go_to_add_questions"), use_container_width=True):
            st.switch_page("pages/add_questions.py")
    st.stop()

official_count = question_repository.count(client, source_types=["official"])
own_count = question_repository.count(client, source_types=["manual"])
pending_review = test_repository.count_pending_review(client)

global_correct, global_total = test_repository.global_accuracy(client)
common_correct, common_total = test_repository.accuracy_by_area(client, "common")
criminal_correct, criminal_total = test_repository.accuracy_by_area(client, "criminal")


def _pct(correct: int, total: int) -> str:
    return f"{correct / total * 100:.0f}%" if total else "—"


row1 = st.columns(4)
row1[0].metric(t("home.stat_documents"), document_count)
row1[1].metric(t("home.stat_active_questions"), total_questions)
row1[2].metric(t("home.stat_official_questions"), official_count)
row1[3].metric(t("home.stat_own_questions"), own_count)

row2 = st.columns(4)
row2[0].metric(t("home.stat_pending_review"), pending_review)
row2[1].metric(t("home.stat_accuracy_global"), _pct(global_correct, global_total))
row2[2].metric(t("home.stat_accuracy_common"), _pct(common_correct, common_total))
row2[3].metric(t("home.stat_accuracy_criminal"), _pct(criminal_correct, criminal_total))

st.divider()

col_a, col_b = st.columns(2)
with col_a:
    if st.button(t("home.review_errors_button"), use_container_width=True):
        st.switch_page("pages/errors.py")
with col_b:
    if st.button(t("home.quick_test_button"), use_container_width=True):
        if test_service.start_quick_test(client, num_questions=10):
            st.switch_page("pages/study.py")
        else:
            st.warning(t("common.no_results"))

st.divider()
st.subheader(t("home.recent_tests"))
recent_sessions = test_repository.list_sessions(client, limit=5)
if not recent_sessions:
    st.caption(t("home.no_recent_tests"))
else:
    for session in recent_sessions:
        date = (session.get("finished_at") or session.get("started_at") or "")[:16].replace("T", " ")
        test_type_label = t(f"test_type.{session['test_type']}")
        score = session.get("penalized_score")
        score_text = f"{score:.2f}" if isinstance(score, (int, float)) else "—"
        st.write(
            t(
                "home.test_summary",
                date=date,
                test_type=test_type_label,
                correct=session.get("correct_answers", 0),
                total=session.get("total_questions", 0),
                score=score_text,
            )
        )
