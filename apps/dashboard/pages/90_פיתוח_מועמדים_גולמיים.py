import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json
from apps.dashboard.ui import apply_rtl, hebrew_columns

st.set_page_config(page_title="פיתוח - מועמדים גולמיים", layout="wide")
apply_rtl()
st.title("פיתוח - מועמדים גולמיים")
st.caption("תצוגה טכנית הכוללת מזהים, שדות פענוח ותאריכים.")

try:
    rows = get_json("/dev/raw-candidates")
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.info("עדיין אין מועמדים.")
    else:
        st.dataframe(hebrew_columns(frame), hide_index=True, use_container_width=True)
except Exception as error:
    st.error(api_error_message(error))
