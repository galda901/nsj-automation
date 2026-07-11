import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json, post_json

st.set_page_config(page_title="Matches", layout="wide")
st.title("Candidate matching")
st.caption("Vector retrieval narrows the list first; scoring stays human-in-the-loop.")

try:
    jobs = get_json("/jobs", params={"job_status": "open"})
    if not jobs:
        st.info("Create an open job first.")
        st.stop()
    options = {
        f"{job['title']} — {job['client_name']} ({job['id']})": job["id"] for job in jobs
    }
    selected = st.selectbox("Job", list(options))
    job_id = options[selected]
    if st.button("Run matching", type="primary"):
        result = post_json(f"/matching/jobs/{job_id}/run", {})
        st.success(f"Scored {result['matches_created']} candidates.")
    matches = get_json(f"/matching/jobs/{job_id}")
    frame = pd.DataFrame(matches)
    if frame.empty:
        st.info("No results yet. Run matching for this job.")
    else:
        st.dataframe(
            frame[["candidate_id", "total_score", "explanation", "created_at"]],
            hide_index=True,
        )
except Exception as error:
    st.error(api_error_message(error))
