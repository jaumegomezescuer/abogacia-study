"""Autenticación por contraseña única (sin usuarios, sin roles).

La contraseña vive solo en `st.secrets` (nunca en el código). La
comparación usa `hmac.compare_digest` para evitar ataques de temporización,
y se aplica un bloqueo temporal tras varios intentos fallidos seguidos como
protección mínima contra fuerza bruta.
"""
from __future__ import annotations

import hmac
import time

import streamlit as st

MAX_ATTEMPTS_BEFORE_LOCKOUT = 5
LOCKOUT_SECONDS = 30


def _get_app_password() -> str | None:
    try:
        password = st.secrets.get("APP_PASSWORD")
    except Exception:
        return None
    return password or None


def is_password_configured() -> bool:
    return _get_app_password() is not None


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated", False))


def logout() -> None:
    st.session_state["authenticated"] = False


def lockout_remaining_seconds() -> int:
    locked_until = st.session_state.get("auth_locked_until", 0)
    return max(0, int(round(locked_until - time.time())))


def attempt_login(candidate: str) -> bool:
    """Comprueba la contraseña y registra el intento. Devuelve si fue correcta."""
    password = _get_app_password()
    # hmac.compare_digest exige cadenas ASCII; se codifica a bytes para admitir
    # contraseñas con acentos u otros caracteres no ASCII sin lanzar TypeError.
    correct = password is not None and hmac.compare_digest(
        candidate.encode("utf-8"), password.encode("utf-8")
    )
    if correct:
        st.session_state["authenticated"] = True
        st.session_state["auth_failed_attempts"] = 0
        st.session_state.pop("auth_locked_until", None)
    else:
        attempts = st.session_state.get("auth_failed_attempts", 0) + 1
        st.session_state["auth_failed_attempts"] = attempts
        if attempts >= MAX_ATTEMPTS_BEFORE_LOCKOUT:
            st.session_state["auth_locked_until"] = time.time() + LOCKOUT_SECONDS
            st.session_state["auth_failed_attempts"] = 0
    return correct
