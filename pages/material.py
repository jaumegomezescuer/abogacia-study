"""Página de Material: subir, listar, previsualizar y eliminar documentos."""
from __future__ import annotations

import streamlit as st

from models.document import AREAS, MATERIAL_TYPES
from repositories import document_repository
from services import file_service
from services.database import get_client
from services.text_extraction import EMPTY_DOCUMENT_WARNING, SCANNED_PDF_WARNING
from services.translation_service import SUPPORTED_LANGUAGES, t

client = get_client()

st.title(t("nav.material"))

uploader_version = st.session_state.get("material_uploader_version", 0)

st.subheader(t("material.upload_title"))
uploaded_file = st.file_uploader(
    t("material.file_label"),
    type=["pdf", "docx", "pptx", "txt", "md"],
    key=f"material_uploader_{uploader_version}",
)

col1, col2 = st.columns(2)
with col1:
    area = st.selectbox(
        t("common.area"), options=list(AREAS),
        format_func=lambda a: t(f"common.area.{a}"), key="material_upload_area",
    )
    existing_topics = document_repository.distinct_topics(client, area=area)
    topic_option = st.selectbox(
        t("common.topic"), options=["__new__"] + existing_topics,
        format_func=lambda v: t("material.new_topic") if v == "__new__" else v,
        key="material_upload_topic_option",
    )
    topic = st.text_input(t("material.topic_free_label"), key="material_upload_topic_free") \
        if topic_option == "__new__" else topic_option
with col2:
    material_type = st.selectbox(
        t("material.material_type"), options=list(MATERIAL_TYPES),
        format_func=lambda m: t(f"material.material_type.{m}"), key="material_upload_type",
    )
    language = st.selectbox(
        t("common.language"), options=list(SUPPORTED_LANGUAGES),
        format_func=lambda code: t(f"common.language.{code}"), key="material_upload_language",
    )

if st.button(t("material.upload_button"), type="primary", disabled=uploaded_file is None):
    try:
        result = file_service.upload_document(
            client, filename=uploaded_file.name, file_bytes=uploaded_file.getvalue(),
            area=area, topic=(topic or None), material_type=material_type, language=language,
        )
    except file_service.FileValidationError as exc:
        st.error(str(exc))
    else:
        if result.processing_status == "error":
            st.warning(t("material.upload_saved_with_error", error=result.processing_error))
        elif SCANNED_PDF_WARNING in result.warnings:
            st.warning(t("material.warning_scanned_pdf"))
        elif EMPTY_DOCUMENT_WARNING in result.warnings:
            st.warning(t("material.warning_empty_document"))
        else:
            st.success(t("material.upload_success"))
        st.session_state["material_uploader_version"] = uploader_version + 1
        st.rerun()

st.divider()
st.subheader(t("material.list_title"))

filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    filter_area = st.selectbox(
        t("common.area"), options=["__all__"] + list(AREAS),
        format_func=lambda a: t("common.all") if a == "__all__" else t(f"common.area.{a}"),
        key="material_filter_area",
    )
with filter_col2:
    search = st.text_input(t("common.search"), key="material_filter_search")

documents = document_repository.list_all(
    client, area=(None if filter_area == "__all__" else filter_area), search=(search or None),
)

if not documents:
    st.caption(t("common.no_results"))

STATUS_ICONS = {"pending": "⏳", "processed": "✅", "error": "⚠️"}

for doc in documents:
    icon = STATUS_ICONS.get(doc["processing_status"], "")
    with st.expander(f"{icon} {doc['original_name']}"):
        info_cols = st.columns(4)
        area_label = t(f"common.area.{doc['area']}")
        material_type_label = t(f"material.material_type.{doc['material_type']}")
        language_label = t(f"common.language.{doc['language']}")
        status_label = t(f"material.status.{doc['processing_status']}")
        page_count_label = doc["page_count"] if doc["page_count"] is not None else "—"
        created_at_label = (doc["created_at"] or "")[:16].replace("T", " ")
        linked_questions = document_repository.count_linked_questions(client, doc["id"])

        info_cols[0].write(f"**{t('common.area')}:** {area_label}")
        info_cols[1].write(f"**{t('common.topic')}:** {doc['topic'] or '—'}")
        info_cols[2].write(f"**{t('material.material_type')}:** {material_type_label}")
        info_cols[3].write(f"**{t('common.language')}:** {language_label}")

        info_cols2 = st.columns(4)
        info_cols2[0].write(f"**{t('material.page_count')}:** {page_count_label}")
        info_cols2[1].write(f"**{t('material.created_at')}:** {created_at_label}")
        info_cols2[2].write(f"**{t('material.status')}:** {status_label}")
        info_cols2[3].write(f"**{t('material.linked_questions')}:** {linked_questions}")

        if doc["processing_status"] == "error" and doc["processing_error"]:
            st.error(doc["processing_error"])

        if doc.get("text_content"):
            with st.expander(t("material.preview_text")):
                st.text_area(
                    t("material.extracted_text_label"), value=doc["text_content"],
                    height=250, disabled=True, key=f"preview_{doc['id']}",
                )
        elif doc["processing_status"] == "processed":
            st.caption(t("material.no_extracted_text"))

        action_cols = st.columns(3)

        with action_cols[0]:
            download_key = f"doc_download_bytes_{doc['id']}"
            if download_key in st.session_state:
                st.download_button(
                    t("common.download"), data=st.session_state[download_key],
                    file_name=doc["original_name"], key=f"download_btn_{doc['id']}",
                )
            else:
                if st.button(t("material.prepare_download"), key=f"prepare_download_{doc['id']}"):
                    full_doc = document_repository.get_by_id(client, doc["id"], include_content=True)
                    st.session_state[download_key] = full_doc["file_content"]
                    st.rerun()

        with action_cols[1]:
            if st.button(t("material.reprocess"), key=f"reprocess_{doc['id']}"):
                try:
                    result = file_service.reprocess_document(client, doc["id"])
                except file_service.FileValidationError as exc:
                    st.error(str(exc))
                else:
                    if result.processing_status == "error":
                        st.warning(t("material.upload_saved_with_error", error=result.processing_error))
                    else:
                        st.success(t("common.success"))
                    st.rerun()

        with action_cols[2]:
            confirm_key = f"confirm_delete_{doc['id']}"
            if st.button(t("common.delete"), key=f"delete_{doc['id']}"):
                st.session_state[confirm_key] = True

        if st.session_state.get(confirm_key):
            st.warning(t("material.confirm_delete", name=doc["original_name"]))
            keep_questions = True
            if linked_questions:
                delete_questions_too = st.checkbox(
                    t("material.also_delete_questions", count=linked_questions),
                    key=f"delete_questions_too_{doc['id']}",
                )
                keep_questions = not delete_questions_too
            confirm_cols = st.columns(2)
            with confirm_cols[0]:
                if st.button(t("common.confirm"), key=f"confirm_delete_btn_{doc['id']}", type="primary"):
                    document_repository.delete(client, doc["id"], keep_questions=keep_questions)
                    st.session_state.pop(confirm_key, None)
                    st.session_state.pop(download_key, None)
                    st.success(t("common.success"))
                    st.rerun()
            with confirm_cols[1]:
                if st.button(t("common.cancel"), key=f"cancel_delete_{doc['id']}"):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
