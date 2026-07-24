"""Traducción de la interfaz (catalán / castellano).

Las preguntas guardan su propio idioma (`language`) de forma independiente:
esto solo controla el idioma de los textos de la interfaz.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import streamlit as st

TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "translations"
FALLBACK_LANGUAGE = "es"
SUPPORTED_LANGUAGES = ("es", "ca")
LANGUAGE_LABELS = {"es": "Castellano", "ca": "Català"}


@lru_cache(maxsize=None)
def _load_translations(language: str) -> dict:
    path = TRANSLATIONS_DIR / f"{language}.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_current_language() -> str:
    return st.session_state.get("language", FALLBACK_LANGUAGE)


def set_language(language: str) -> None:
    st.session_state["language"] = language if language in SUPPORTED_LANGUAGES else FALLBACK_LANGUAGE


def t(key: str, **kwargs) -> str:
    """Traduce `key` al idioma actual de la interfaz.

    Usa castellano como idioma de respaldo si falta la clave, y devuelve
    la propia clave si no existe traducción en ningún idioma.
    """
    language = get_current_language()
    text = _load_translations(language).get(key)
    if text is None:
        text = _load_translations(FALLBACK_LANGUAGE).get(key)
    if text is None:
        return key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
