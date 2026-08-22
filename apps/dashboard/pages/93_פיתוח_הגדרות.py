import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json
from apps.dashboard.ui import apply_rtl, hebrew_columns

st.set_page_config(page_title="פיתוח - הגדרות", layout="wide")
apply_rtl()
st.title("פיתוח - הגדרות")

try:
    settings = get_json("/dev/settings")
    settings_frame = pd.DataFrame({"ערך": list(settings.values()), "הגדרה": list(settings)})
    st.dataframe(
        hebrew_columns(settings_frame),
        hide_index=True,
        use_container_width=True,
    )
except Exception as error:
    st.error(api_error_message(error))
