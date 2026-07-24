"""Acceso a datos de la tabla `app_settings` (clave/valor)."""
from __future__ import annotations

from typing import Optional

from services.database import execute, row_to_dict


def get(client, key: str, default: Optional[str] = None) -> Optional[str]:
    row = row_to_dict(execute(client, "SELECT value FROM app_settings WHERE key = ?", [key]))
    return row["value"] if row else default


def set(client, key: str, value: str) -> None:
    execute(
        client,
        """
        INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """,
        [key, value],
    )


def get_all(client) -> dict:
    from services.database import rows_to_dicts
    rows = rows_to_dicts(execute(client, "SELECT key, value FROM app_settings"))
    return {row["key"]: row["value"] for row in rows}


def delete(client, key: str) -> None:
    execute(client, "DELETE FROM app_settings WHERE key = ?", [key])
