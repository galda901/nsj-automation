import pandas as pd
import streamlit as st

from apps.dashboard.api_client import API_BASE_URL, api_error_message, get_json, post_empty

st.set_page_config(page_title="Candidates", layout="wide")
st.title("Candidates")
st.caption("A clean recruiter view. Technical fields are hidden here.")
left, right = st.columns(2)
q = left.text_input("Search", placeholder="Name, email, title, or CV text")
candidate_status = right.selectbox(
    "Status", ["", "new", "active", "submitted", "rejected", "hired"]
)

try:
    candidates = get_json(
        "/candidates/with-files",
        params={"q": q or None, "candidate_status": candidate_status or None},
    )
    frame = pd.DataFrame(candidates)
    if frame.empty:
        st.info("No candidates yet. Upload a CV from the CV Ingestion page.")
    else:
        view = frame.rename(
            columns={
                "full_name": "Name",
                "email": "Email",
                "city": "City",
                "current_title": "Profession",
                "seniority": "Seniority",
                "status": "Status",
                "latest_cv_path": "CV",
            }
        )
        friendly_columns = [
            "Name",
            "Email",
            "City",
            "Profession",
            "Seniority",
            "Status",
            "CV",
        ]
        st.dataframe(
            view[[column for column in friendly_columns if column in view]],
            hide_index=True,
            use_container_width=True,
        )
        st.divider()
        options = {
            f"{row.get('full_name') or 'Candidate'} ({row.get('email') or row.get('id')})": row
            for row in candidates
        }
        selected = st.selectbox("Open or download a candidate CV", list(options))
        selected_row = options[selected]
        candidate_id = selected_row["id"]
        if selected_row.get("latest_cv_path"):
            st.code(selected_row["latest_cv_path"], language=None)
            col1, col2 = st.columns(2)
            if col1.button("Open CV on this PC", type="primary"):
                try:
                    result = post_empty(f"/candidates/{candidate_id}/latest-cv/open")
                    if result.get("opened"):
                        st.success("Opened CV.")
                    else:
                        st.info(result.get("detail", "Open action did not run."))
                except Exception as error:
                    st.error(api_error_message(error))
            col2.link_button(
                "Download CV",
                f"{API_BASE_URL}/candidates/{candidate_id}/latest-cv/download",
            )
        else:
            st.info("This candidate does not have a linked CV file yet.")
except Exception as error:
    st.error(api_error_message(error))
