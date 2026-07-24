"""Página Añadir preguntas: importación por CSV/JSON y alta manual."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from models.question import AREAS, DIFFICULTIES, OPTIONS, QUESTION_TYPES
from repositories import question_repository
from services import question_service
from services.database import get_client
from services.translation_service import SUPPORTED_LANGUAGES, t

client = get_client()

st.title(t("nav.add_questions"))

tab_import, tab_manual = st.tabs([t("add_questions.tab_import"), t("add_questions.tab_manual")])

with tab_import:
    template_path = Path(__file__).resolve().parent.parent / "data" / "exports" / "plantilla_preguntas.csv"
    if template_path.exists():
        st.download_button(
            t("add_questions.download_template"), data=template_path.read_bytes(),
            file_name="plantilla_preguntas.csv", mime="text/csv",
        )

    uploaded = st.file_uploader(t("add_questions.import_file_label"), type=["csv", "json"], key="import_file")

    if uploaded is None:
        st.caption(t("add_questions.import_hint"))
    else:
        try:
            rows = question_service.parse_import_file(uploaded.name, uploaded.getvalue())
        except question_service.ImportFormatError as exc:
            st.error(str(exc))
            rows = []

        if rows:
            results = question_service.validate_rows(rows)
            valid_count = sum(1 for r in results if r.is_valid)
            invalid_count = len(results) - valid_count
            st.info(
                t("add_questions.preview_summary", total=len(results), valid=valid_count, invalid=invalid_count)
            )

            included_flags = []
            for result in results:
                preview = (result.data.get("statement") or "")[:80]
                icon = "✅" if result.is_valid else "❌"
                with st.expander(f"{icon} {t('add_questions.row_label', number=result.row_number)}: {preview}"):
                    st.json(result.data, expanded=False)
                    for err in result.errors:
                        st.error(err)
                    include = st.checkbox(
                        t("add_questions.include_row"), value=result.is_valid,
                        disabled=not result.is_valid, key=f"include_row_{uploaded.name}_{result.row_number}",
                    )
                    included_flags.append(include and result.is_valid)

            if st.button(t("add_questions.import_button"), type="primary", disabled=valid_count == 0):
                to_import = [
                    question_service.build_manual_question_fields(result.data)
                    for result, include in zip(results, included_flags) if include
                ]
                ids = question_repository.bulk_create(client, to_import)
                st.success(t("add_questions.import_success", count=len(ids)))
                st.rerun()

with tab_manual:
    with st.form("manual_question_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            area = st.selectbox(
                t("common.area"), options=list(AREAS), format_func=lambda a: t(f"common.area.{a}"),
            )
            topic = st.text_input(t("common.topic"))
            subtopic = st.text_input(t("add_questions.subtopic_label"))
            language = st.selectbox(
                t("common.language"), options=list(SUPPORTED_LANGUAGES),
                format_func=lambda code: t(f"common.language.{code}"),
            )
        with col2:
            question_type = st.selectbox(
                t("common.question_type"), options=list(QUESTION_TYPES),
                format_func=lambda q: t(f"common.question_type.{q}"),
            )
            difficulty = st.selectbox(
                t("common.difficulty"), options=list(DIFFICULTIES),
                format_func=lambda d: t(f"common.difficulty.{d}"),
            )
            source_reference = st.text_input(t("add_questions.source_reference_label"))
            source_page = st.text_input(t("add_questions.source_page_label"))

        statement = st.text_area(t("add_questions.statement_label"))

        opt_col1, opt_col2 = st.columns(2)
        with opt_col1:
            option_a = st.text_input("A")
            option_c = st.text_input("C")
        with opt_col2:
            option_b = st.text_input("B")
            option_d = st.text_input("D")

        correct_option = st.radio(t("add_questions.correct_option_label"), options=list(OPTIONS), horizontal=True)
        explanation = st.text_area(t("add_questions.explanation_label"))
        incorrect_explanations = st.text_area(t("add_questions.incorrect_explanations_label"))
        legal_reference = st.text_input(t("add_questions.legal_reference_label"))

        submitted = st.form_submit_button(t("common.save"), type="primary")

    if submitted:
        data = {
            "area": area, "topic": topic, "subtopic": subtopic, "language": language,
            "question_type": question_type, "difficulty": difficulty, "statement": statement,
            "option_a": option_a, "option_b": option_b, "option_c": option_c, "option_d": option_d,
            "correct_option": correct_option, "explanation": explanation,
            "incorrect_explanations": incorrect_explanations, "source_reference": source_reference,
            "source_page": source_page, "legal_reference": legal_reference,
        }
        errors = question_service.validate_question_data(data)
        if errors:
            for err in errors:
                st.error(err)
        else:
            fields = question_service.build_manual_question_fields(data)
            question_repository.create(client, fields)
            st.success(t("add_questions.manual_save_success"))
