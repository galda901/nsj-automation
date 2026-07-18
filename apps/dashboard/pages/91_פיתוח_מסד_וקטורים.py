import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json, post_empty
from apps.dashboard.ui import apply_rtl, hebrew_columns

st.set_page_config(page_title="פיתוח - מסד וקטורים", layout="wide")
apply_rtl()
st.title("פיתוח - מסד וקטורים")
st.caption("רשומות הטמעה מקומיות ב־SQLite, המשמשות לאיתור לפני התאמה.")

if st.button("בנייה מחדש של ההטמעות", type="primary"):
    try:
        st.json(post_empty("/dev/vectors/rebuild"))
    except Exception as error:
        st.error(api_error_message(error))

try:
    rows = get_json("/dev/vectors")
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.info("עדיין אין רשומות וקטוריות.")
    else:
        display_columns = [
            "owner_type",
            "owner_id",
            "source_type",
            "embedding_model",
            "dimensions",
            "preview_text",
            "created_at",
            "id",
        ]
        st.dataframe(
            hebrew_columns(frame[[column for column in display_columns if column in frame]]),
            hide_index=True,
            use_container_width=True,
        )
except Exception as error:
    st.error(api_error_message(error))
