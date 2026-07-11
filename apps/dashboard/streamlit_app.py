import streamlit as st

from apps.dashboard.api_client import API_BASE_URL, api_error_message, get_json

st.set_page_config(page_title="NSJ Recruitment", page_icon="🧲", layout="wide")
st.sidebar.title("NSJ Recruitment")
st.title("NSJ Recruitment")
st.caption("Simple daily recruiting operations, with technical tools tucked away.")

try:
    health = get_json("/health")
    st.success(f"API connected at {API_BASE_URL} · {health['status']}")
except Exception as error:
    st.error(api_error_message(error))

st.markdown(
    """
Use the first pages in the sidebar for daily work:

- Candidates
- Jobs
- Matches
- Inbox Intake

Developer-only pages are grouped later with the `Dev -` prefix.
"""
)
