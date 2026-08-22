import json

import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json
from apps.dashboard.ui import apply_rtl, hebrew_columns


st.set_page_config(page_title="פיתוח - התראות", layout="wide")
apply_rtl()
st.title("פיתוח - worker והתראות Telegram")

try:
    worker = get_json("/dev/worker-status")
    settings = get_json("/dev/settings")
    last_summary = (
        json.loads(worker["last_summary_json"])
        if worker.get("last_summary_json")
        else {}
    )
    status_columns = st.columns(5)
    status_columns[0].metric("סטטוס worker", worker.get("status", "לא הופעל"))
    status_columns[1].metric("Telegram פעיל", "כן" if settings.get("telegram_enabled") else "לא")
    status_columns[2].metric("מצב בדיקה", "כן" if settings.get("telegram_dry_run") else "לא")
    status_columns[3].metric(
        "התראות שנוצרו", last_summary.get("notifications_created", 0)
    )
    status_columns[4].metric("Chat ID מוגדר", "כן" if settings.get("telegram_chat_id_configured") else "לא")

    if worker.get("last_error"):
        st.error(worker["last_error"])
    if worker.get("last_summary_json"):
        with st.expander("סיכום הריצה האחרונה"):
            st.json(last_summary)

    rows = get_json("/dev/telegram-notifications")
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.info("עדיין לא נוצרו התראות.")
    else:
        display_columns = [
            "status",
            "candidate_name",
            "job_title",
            "score",
            "attempts",
            "recipient",
            "last_error",
            "created_at",
            "sent_at",
            "message_body",
        ]
        st.dataframe(
            hebrew_columns(frame[[column for column in display_columns if column in frame]]),
            hide_index=True,
            use_container_width=True,
        )
except Exception as error:
    st.error(api_error_message(error))
