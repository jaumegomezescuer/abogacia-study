"""Página Preguntas oficiales: importación y consulta de exámenes reales."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from models.question import AREAS, QUESTION_STATUSES
from repositories import question_repository
from services import question_service
from services.database import get_client
from services.translation_service import t

client = get_client()

st.title(t("nav.official_questions"))

tab_import, tab_list = st.tabs([t("official.tab_import"), t("official.tab_list")])

with tab_import:
    template_path = Path(__file__).resolve().parent.parent / "data" / "exports" / "plantilla_preguntas_oficiales.csv"
    if template_path.exists():
        st.download_button(
            t("add_questions.download_template"), data=template_path.read_bytes(),
            file_name="plantilla_preguntas_oficiales.csv", mime="text/csv",
        )

    uploaded = st.file_uploader(t("add_questions.import_file_label"), type=["csv", "json"], key="official_import_file")

    if uploaded is None:
        st.caption(t("official.import_hint"))
    else:
        try:
            rows = question_service.parse_import_file(uploaded.name, uploaded.getvalue())
        except question_service.ImportFormatError as exc:
            st.error(str(exc))
            rows = []

        if rows:
            results = question_service.validate_rows(rows, require_official_fields=True)
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
                        disabled=not result.is_valid, key=f"official_include_row_{uploaded.name}_{result.row_number}",
                    )
                    included_flags.append(include and result.is_valid)

            if st.button(t("add_questions.import_button"), type="primary", disabled=valid_count == 0):
                to_import = [
                    question_service.build_official_question_fields(result.data)
                    for result, include in zip(results, included_flags) if include
                ]
                ids = question_repository.bulk_create(client, to_import)
                st.success(t("add_questions.import_success", count=len(ids)))
                st.rerun()

with tab_list:
    exam_years = question_repository.distinct_exam_years(client)

    col1, col2, col3 = st.columns(3)
    with col1:
        area_choice = st.selectbox(
            t("common.area"), options=["both"] + list(AREAS),
            format_func=lambda a: t("common.area.both") if a == "both" else t(f"common.area.{a}"),
            key="official_filter_area",
        )
        areas = None if area_choice == "both" else [area_choice]
    with col2:
        year_choice = st.selectbox(
            t("official.year_label"), options=["all"] + exam_years,
            format_func=lambda y: t("common.all") if y == "all" else str(y),
            key="official_filter_year",
        )
    with col3:
        status_choice = st.selectbox(
            t("official.status_filter_label"), options=["all"] + list(QUESTION_STATUSES),
            format_func=lambda s: t("common.all") if s == "all" else t(f"official.status.{s}"),
            key="official_filter_status",
        )
        statuses = None if status_choice == "all" else [status_choice]

    questions = question_repository.list_questions(
        client, areas=areas, source_types=["official"], statuses=statuses,
        exclude_annulled=False, is_active=None,
    )
    if year_choice != "all":
        questions = [q for q in questions if q.get("exam_year") == year_choice]

    st.caption(t("official.count_summary", count=len(questions)))

    if not questions:
        st.caption(t("common.no_results"))

    STATUS_ICONS = {"valid": "✅", "annulled": "🚫", "reserve": "🕓"}

    for question in questions:
        icon = STATUS_ICONS.get(question["status"], "")
        header = f"{icon} {question.get('exam_name') or '—'} ({question.get('exam_year') or '—'}) — {question['statement'][:70]}"
        with st.expander(header):
            info_cols = st.columns(4)
            area_label = t(f"common.area.{question['area']}")
            info_cols[0].write(f"**{t('common.area')}:** {area_label}")
            info_cols[1].write(f"**{t('common.topic')}:** {question['topic'] or '—'}")
            info_cols[2].write(f"**{t('official.call_label')}:** {question.get('exam_call') or '—'}")
            status_label = t(f"official.status.{question['status']}")
            info_cols[3].write(f"**{t('official.status_filter_label')}:** {status_label}")

            option_labels = {opt: question[f"option_{opt.lower()}"] for opt in ("A", "B", "C", "D")}
            for opt, text in option_labels.items():
                prefix = "✅" if opt == question["correct_option"] else "◻️"
                st.write(f"{prefix} **{opt}.** {text}")
            if question.get("legal_reference"):
                st.caption(f"{t('add_questions.legal_reference_label')}: {question['legal_reference']}")
            if question.get("source_reference"):
                st.caption(f"{t('add_questions.source_reference_label')}: {question['source_reference']}")

            if st.button(t("common.delete"), key=f"delete_official_{question['id']}"):
                question_repository.delete(client, question["id"])
                st.rerun()
