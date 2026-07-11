import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json

st.set_page_config(page_title="Dev - Settings", layout="wide")
st.title("Dev - Settings")

try:
    st.json(get_json("/dev/settings"))
except Exception as error:
    st.error(api_error_message(error))
