import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json
from apps.dashboard.ui import apply_rtl

st.set_page_config(page_title="פיתוח - הגדרות", layout="wide")
apply_rtl()
st.title("פיתוח - הגדרות")

try:
    settings = get_json("/dev/settings")
    st.dataframe(
        {"ערך": list(settings.values()), "הגדרה": list(settings)},
        hide_index=True,
        use_container_width=True,
    )
except Exception as error:
    st.error(api_error_message(error))
