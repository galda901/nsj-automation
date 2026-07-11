import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json

st.set_page_config(page_title="Dev - Raw Candidates", layout="wide")
st.title("Dev - Raw Candidates")
st.caption("Technical view with IDs, parser fields, and timestamps.")

try:
    rows = get_json("/dev/raw-candidates")
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.info("No candidates yet.")
    else:
        st.dataframe(frame, hide_index=True, use_container_width=True)
except Exception as error:
    st.error(api_error_message(error))
