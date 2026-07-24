"""Página de Estadísticas: progreso de estudio con componentes nativos de Streamlit."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.database import get_client
from services.statistics_service import get_summary
from services.translation_service import t

client = get_client()

st.title(t("nav.statistics"))

summary = get_summary(client)

if summary["answered"] == 0:
    st.info(t("stats.no_data"))
    st.stop()


def _pct(correct: int, total: int) -> float | None:
    return (correct / total * 100) if total else None


row1 = st.columns(4)
row1[0].metric(t("stats.answered"), summary["answered"])
row1[1].metric(t("stats.correct"), summary["correct"])
row1[2].metric(t("stats.incorrect"), summary["incorrect"])
row1[3].metric(t("stats.blank"), summary["blank"])

row2 = st.columns(4)
accuracy_text = f"{summary['accuracy_pct']:.0f}%" if summary["accuracy_pct"] is not None else "—"
row2[0].metric(t("stats.accuracy_pct"), accuracy_text)
avg_score = summary["average_penalized_score"]
row2[1].metric(t("stats.average_score"), f"{avg_score:.2f}" if avg_score is not None else "—")
avg_time = summary["average_response_time_seconds"]
row2[2].metric(t("stats.average_response_time"), f"{avg_time:.1f}s" if avg_time is not None else "—")
row2[3].metric(t("stats.mock_exam_count"), summary["mock_exam_count"])

st.divider()
st.subheader(t("stats.by_area"))
area_cols = st.columns(2)
for col, area in zip(area_cols, ("common", "criminal")):
    correct, total = summary["by_area"][area]
    pct = _pct(correct, total)
    col.metric(t(f"common.area.{area}"), f"{pct:.0f}%" if pct is not None else "—", help=t("stats.based_on_n", n=total))

st.divider()


def _render_breakdown(title: str, rows: list[dict], key_field: str, label_func) -> None:
    st.subheader(title)
    if not rows:
        st.caption(t("stats.no_data"))
        return
    data = {
        label_func(row[key_field]): _pct(row["correct"], row["total"]) or 0
        for row in rows if row[key_field]
    }
    df = pd.DataFrame({"pct": data})
    st.bar_chart(df)


_render_breakdown(t("stats.by_topic"), summary["by_topic"], "topic", lambda v: v)
_render_breakdown(t("stats.by_difficulty"), summary["by_difficulty"], "difficulty", lambda v: t(f"common.difficulty.{v}"))
_render_breakdown(t("stats.by_question_type"), summary["by_question_type"], "question_type", lambda v: t(f"common.question_type.{v}"))

st.divider()
st.subheader(t("stats.evolution"))
recent = summary["recent_sessions"]
if recent:
    df = pd.DataFrame({
        "test": list(range(1, len(recent) + 1)),
        "score": [s.get("penalized_score") or 0 for s in recent],
    }).set_index("test")
    st.line_chart(df)
else:
    st.caption(t("stats.no_data"))

st.divider()
st.subheader(t("stats.most_failed_title"))
most_failed = summary["most_failed_questions"]
if most_failed:
    for question in most_failed:
        st.write(f"❌ ({question['times_incorrect']}) {question['statement'][:100]}")
else:
    st.caption(t("stats.no_data"))

st.divider()
st.metric(t("stats.correct_with_low_confidence"), summary["correct_with_low_confidence"])
