"""Punto de entrada de la aplicación de estudio para el acceso a la abogacía."""
from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

from repositories import document_repository, question_repository
from services import auth_service
from services.database import DatabaseError, get_client
from services.translation_service import (
    LANGUAGE_LABELS,
    SUPPORTED_LANGUAGES,
    get_current_language,
    set_language,
    t,
)

LOG_PATH = Path(__file__).resolve().parent / "data" / "app.log"


def _configure_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(LOG_PATH),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


_configure_logging()

st.set_page_config(page_title="Acceso a la Abogacía - Estudio", page_icon="⚖️", layout="wide")

if "language" not in st.session_state:
    set_language("es")


def _render_login() -> None:
    st.title(t("auth.title"))
    st.write(t("auth.description"))
    if not auth_service.is_password_configured():
        st.error(t("auth.missing_config"))
        st.stop()

    remaining = auth_service.lockout_remaining_seconds()
    if remaining > 0:
        st.warning(t("auth.wait", seconds=remaining))

    with st.form("login_form"):
        password = st.text_input(t("auth.password_label"), type="password", disabled=remaining > 0)
        submitted = st.form_submit_button(t("auth.submit"), disabled=remaining > 0)

    if submitted and remaining == 0:
        if auth_service.attempt_login(password):
            st.rerun()
        else:
            st.error(t("auth.error"))
    st.stop()


if not auth_service.is_authenticated():
    _render_login()

try:
    _client = get_client()
except DatabaseError as exc:
    st.error(str(exc))
    st.stop()

with st.sidebar:
    st.title(t("app.title"))
    st.caption(t("app.subtitle"))
    st.divider()

    language_codes = list(SUPPORTED_LANGUAGES)
    selected_language = st.selectbox(
        t("nav.language"),
        options=language_codes,
        format_func=lambda code: LANGUAGE_LABELS[code],
        index=language_codes.index(get_current_language()),
        key="language_selector",
    )
    if selected_language != get_current_language():
        set_language(selected_language)
        st.rerun()

    st.divider()
    st.caption(t("nav.summary_title"))
    st.write(t("nav.summary_documents", count=document_repository.count(_client)))
    st.write(t("nav.summary_questions", count=question_repository.count(_client)))

    st.divider()
    if st.button(t("nav.logout"), use_container_width=True):
        auth_service.logout()
        st.rerun()

pages = [
    st.Page("pages/home.py", title=t("nav.home"), icon="🏠", default=True, url_path="inicio"),
    st.Page("pages/material.py", title=t("nav.material"), icon="📄", url_path="material"),
    st.Page("pages/add_questions.py", title=t("nav.add_questions"), icon="➕", url_path="anadir-preguntas"),
    st.Page("pages/study.py", title=t("nav.study"), icon="📝", url_path="estudiar"),
    st.Page("pages/mock_exam.py", title=t("nav.mock_exam"), icon="⏱️", url_path="simulacro"),
    st.Page("pages/official_questions.py", title=t("nav.official_questions"), icon="🏛️", url_path="oficiales"),
    st.Page("pages/errors.py", title=t("nav.errors"), icon="🔁", url_path="errores"),
    st.Page("pages/statistics.py", title=t("nav.statistics"), icon="📊", url_path="estadisticas"),
    st.Page("pages/settings.py", title=t("nav.settings"), icon="⚙️", url_path="configuracion"),
]

navigation = st.navigation(pages)
navigation.run()
