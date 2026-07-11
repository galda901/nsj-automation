import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json, post_empty, post_json

st.set_page_config(page_title="Jobs", layout="wide")
st.title("Jobs")
st.caption("Draft jobs from email stay here until reviewed and opened.")

with st.expander("Create a new job", expanded=True):
    with st.form("create-job", clear_on_submit=True):
        client_name = st.text_input("Client name")
        title = st.text_input("Job title")
        location = st.text_input("Location")
        seniority = st.selectbox(
            "Seniority", ["", "junior", "mid", "senior", "lead", "manager"]
        )
        min_years = st.number_input("Minimum years of experience", min_value=0.0, step=0.5)
        description = st.text_area("Job description")
        submitted = st.form_submit_button("Create job", type="primary")
    if submitted:
        if not client_name.strip() or not title.strip() or not description.strip():
            st.error("Client, title, and description are required.")
        else:
            try:
                created = post_json(
                    "/jobs",
                    {
                        "client_name": client_name,
                        "title": title,
                        "location": location or None,
                        "seniority": seniority or None,
                        "min_years_experience": min_years or None,
                        "description": description,
                    },
                )
                st.success(f"Created {created['title']} ({created['id']})")
            except Exception as error:
                st.error(api_error_message(error))

try:
    jobs = get_json("/jobs")
    frame = pd.DataFrame(jobs)
    if frame.empty:
        st.info("No jobs yet.")
    else:
        preferred = ["title", "client_name", "location", "seniority", "status", "id"]
        st.dataframe(
            frame[[column for column in preferred if column in frame]],
            hide_index=True,
            use_container_width=True,
        )
        draft_jobs = [job for job in jobs if job.get("status") == "draft"]
        if draft_jobs:
            st.divider()
            st.subheader("Review draft jobs")
            options = {
                f"{job['title']} — {job['client_name']} ({job['id']})": job["id"]
                for job in draft_jobs
            }
            selected = st.selectbox("Draft job to open", list(options))
            if st.button("Mark selected job as open", type="primary"):
                try:
                    opened = post_empty(f"/jobs/{options[selected]}/open")
                    st.success(f"Opened job: {opened['title']}")
                    st.rerun()
                except Exception as error:
                    st.error(api_error_message(error))
except Exception as error:
    st.error(api_error_message(error))
