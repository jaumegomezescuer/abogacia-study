"""Configuración persistente de la aplicación (simulacro, preferencias)."""
from __future__ import annotations

import json
from dataclasses import asdict

from models.settings import MockExamConfig
from repositories import settings_repository

MOCK_EXAM_CONFIG_KEY = "mock_exam_config"


def get_mock_exam_config(client) -> MockExamConfig:
    raw = settings_repository.get(client, MOCK_EXAM_CONFIG_KEY)
    if not raw:
        return MockExamConfig()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return MockExamConfig()
    defaults = asdict(MockExamConfig())
    defaults.update({k: v for k, v in data.items() if k in defaults})
    return MockExamConfig(**defaults)


def save_mock_exam_config(client, config: MockExamConfig) -> None:
    settings_repository.set(client, MOCK_EXAM_CONFIG_KEY, json.dumps(asdict(config)))
