"""Página de Configuración: idioma, simulacro, exportación y borrado de datos."""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from models.settings import MockExamConfig
from services import export_service
from services.database import get_client
from services.settings_service import get_mock_exam_config, save_mock_exam_config
from services.translation_service import LANGUAGE_LABELS, SUPPORTED_LANGUAGES, get_current_language, set_language, t

client = get_client()

st.title(t("nav.settings"))

st.subheader(t("settings.language_title"))
language_codes = list(SUPPORTED_LANGUAGES)
selected_language = st.selectbox(
    t("nav.language"), options=language_codes, format_func=lambda code: LANGUAGE_LABELS[code],
    index=language_codes.index(get_current_language()), key="settings_language_selector",
)
if selected_language != get_current_language():
    set_language(selected_language)
    st.rerun()

st.divider()
st.subheader(t("settings.mock_exam_title"))
config = get_mock_exam_config(client)

col1, col2 = st.columns(2)
with col1:
    common_scored = st.number_input(
        t("settings.common_scored"), min_value=1, max_value=200, value=config.common_scored_questions,
    )
    common_reserve = st.number_input(
        t("settings.common_reserve"), min_value=0, max_value=50, value=config.common_reserve_questions,
    )
    common_minutes = st.number_input(
        t("settings.common_minutes"), min_value=1, max_value=600, value=config.common_time_minutes,
    )
with col2:
    criminal_scored = st.number_input(
        t("settings.criminal_scored"), min_value=1, max_value=200, value=config.criminal_scored_questions,
    )
    criminal_reserve = st.number_input(
        t("settings.criminal_reserve"), min_value=0, max_value=50, value=config.criminal_reserve_questions,
    )
    criminal_minutes = st.number_input(
        t("settings.criminal_minutes"), min_value=1, max_value=600, value=config.criminal_time_minutes,
    )

col3, col4 = st.columns(2)
with col3:
    correct_score = st.number_input(t("settings.correct_score"), min_value=0.0, max_value=10.0, value=config.correct_score, step=0.1)
    incorrect_penalty = st.number_input(t("settings.incorrect_penalty"), min_value=0.0, max_value=1.0, value=config.incorrect_penalty, step=0.05)
    blank_score = st.number_input(t("settings.blank_score"), min_value=0.0, max_value=10.0, value=config.blank_score, step=0.1)
with col4:
    common_weight_pct = st.slider(t("settings.common_weight"), min_value=0, max_value=100, value=int(round(config.common_weight * 100)))
    use_annulled = st.checkbox(t("settings.use_annulled"), value=config.use_annulled_questions)
    master_note_threshold = st.number_input(
        t("settings.master_note_threshold"), min_value=0.0, max_value=10.0, value=config.master_note_threshold, step=0.1,
    )

if st.button(t("common.save"), type="primary", key="save_mock_exam_config"):
    new_config = MockExamConfig(
        common_scored_questions=int(common_scored), common_reserve_questions=int(common_reserve),
        criminal_scored_questions=int(criminal_scored), criminal_reserve_questions=int(criminal_reserve),
        common_time_minutes=int(common_minutes), criminal_time_minutes=int(criminal_minutes),
        correct_score=float(correct_score), incorrect_penalty=float(incorrect_penalty),
        blank_score=float(blank_score), common_weight=common_weight_pct / 100,
        criminal_weight=1 - common_weight_pct / 100, use_annulled_questions=use_annulled,
        master_note_threshold=float(master_note_threshold),
    )
    save_mock_exam_config(client, new_config)
    st.success(t("common.success"))

st.divider()
st.subheader(t("settings.export_title"))
today = datetime.now(timezone.utc).strftime("%Y%m%d")

export_cols = st.columns(3)
with export_cols[0]:
    st.download_button(
        t("settings.export_questions_csv"), data=export_service.export_questions_csv(client),
        file_name=f"preguntas_{today}.csv", mime="text/csv",
    )
with export_cols[1]:
    st.download_button(
        t("settings.export_questions_json"), data=export_service.export_questions_json(client),
        file_name=f"preguntas_{today}.json", mime="application/json",
    )
with export_cols[2]:
    st.download_button(
        t("settings.export_full_database"), data=export_service.export_full_database_json(client),
        file_name=f"backup_completo_{today}.json", mime="application/json",
    )

if st.button(t("settings.go_to_import")):
    st.switch_page("pages/add_questions.py")

st.divider()
st.subheader(t("settings.danger_zone_title"))
st.warning(t("settings.danger_zone_description"))

confirm_delete_all = st.checkbox(t("settings.confirm_delete_all_checkbox"), key="settings_confirm_delete_all")
if st.button(t("settings.delete_all_button"), disabled=not confirm_delete_all, type="primary"):
    export_service.delete_all_data(client)
    # Cualquier test o simulacro en curso apuntaría a datos que ya no existen.
    st.session_state.pop("active_test", None)
    st.session_state.pop("mock_exam", None)
    st.session_state.pop("settings_confirm_delete_all", None)
    st.success(t("settings.delete_all_success"))
    st.rerun()
