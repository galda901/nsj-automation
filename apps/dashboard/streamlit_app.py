import streamlit as st

from apps.dashboard.api_client import API_BASE_URL, api_error_message, get_json
from apps.dashboard.ui import apply_rtl

st.set_page_config(page_title="NSJ גיוס", page_icon="🧩", layout="wide")
apply_rtl()
st.sidebar.title("NSJ Recruitment")
st.title("NSJ Recruitment")
st.caption("פעילות גיוס יומית פשוטה, עם כלי פיתוח נפרדים.")

try:
    health = get_json("/health")
    st.success(f"ה־API מחובר ב־{API_BASE_URL} · {health['status']}")
except Exception as error:
    st.error(api_error_message(error))

st.markdown(
    """
העמודים הראשונים בסרגל הצד מיועדים לעבודה היומית:

- מועמדים
- משרות
- התאמות
- קליטת דואר

עמודי פיתוח נמצאים בהמשך, תחת הקידומת `פיתוח -`.
"""
)
