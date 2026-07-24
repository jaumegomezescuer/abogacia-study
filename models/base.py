"""Utilidad común para construir modelos a partir de filas de la base de datos."""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass
class BaseModel:
    @classmethod
    def from_row(cls, row: dict):
        field_names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in row.items() if k in field_names})
