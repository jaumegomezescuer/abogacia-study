"""Orquesta la subida, el procesamiento y la eliminación de documentos."""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from repositories import document_repository
from services.text_extraction import SUPPORTED_EXTENSIONS, UnsupportedFileTypeError, extract_text

logger = logging.getLogger("abogacia")

# Margen prudente para no acercarse a los límites de fila del plan gratuito de Turso.
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


class FileValidationError(Exception):
    pass


@dataclass
class UploadResult:
    document_id: int
    processing_status: str
    processing_error: Optional[str]
    warnings: list[str]
    page_count: Optional[int]


def validate_upload(filename: str, size_bytes: int) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise FileValidationError(
            f"Formato no admitido ({suffix or 'sin extensión'}). "
            f"Formatos permitidos: {', '.join(SUPPORTED_EXTENSIONS)}."
        )
    if size_bytes <= 0:
        raise FileValidationError("El archivo está vacío.")
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise FileValidationError(
            f"El archivo pesa {size_bytes / 1024 / 1024:.1f} MB y el límite son "
            f"{MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB, para no acercarse a los límites "
            "del plan gratuito de Turso."
        )


def _run_extraction(filename: str, file_bytes: bytes) -> tuple[Optional[int], Optional[str], str, Optional[str], list[str]]:
    """Devuelve (page_count, text_content, processing_status, processing_error, warnings)."""
    try:
        extracted = extract_text(filename, io.BytesIO(file_bytes))
        return extracted.page_count, extracted.text, "processed", None, extracted.warnings
    except UnsupportedFileTypeError as exc:
        return None, None, "error", str(exc), []
    except Exception as exc:  # PDF corrupto, DOCX/PPTX inválido, etc.
        logger.exception("Error extrayendo texto de %s", filename)
        return None, None, "error", f"No se pudo extraer el texto: {exc}", []


def upload_document(client, *, filename: str, file_bytes: bytes, area: str,
                     topic: Optional[str], material_type: str, language: str) -> UploadResult:
    validate_upload(filename, len(file_bytes))
    file_type = Path(filename).suffix.lower().lstrip(".")

    page_count, text_content, processing_status, processing_error, warnings = _run_extraction(filename, file_bytes)

    document_id = document_repository.create(
        client, original_name=filename, stored_name=filename, file_type=file_type,
        file_content=file_bytes, area=area, topic=(topic or None), material_type=material_type,
        language=language, page_count=page_count, text_content=text_content,
        processing_status=processing_status, processing_error=processing_error,
    )
    return UploadResult(
        document_id=document_id, processing_status=processing_status,
        processing_error=processing_error, warnings=warnings, page_count=page_count,
    )


def reprocess_document(client, document_id: int) -> UploadResult:
    doc = document_repository.get_by_id(client, document_id, include_content=True)
    if doc is None or doc.get("file_content") is None:
        raise FileValidationError("El documento ya no tiene un archivo disponible para reprocesar.")

    page_count, text_content, processing_status, processing_error, warnings = _run_extraction(
        doc["original_name"], doc["file_content"]
    )
    document_repository.update_processing_result(
        client, document_id, page_count=page_count, text_content=text_content,
        processing_status=processing_status, processing_error=processing_error,
    )
    return UploadResult(
        document_id=document_id, processing_status=processing_status,
        processing_error=processing_error, warnings=warnings, page_count=page_count,
    )
