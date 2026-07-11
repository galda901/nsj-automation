import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, post_empty, upload_cv

st.set_page_config(page_title="Inbox Intake", layout="wide")
st.title("Inbox Intake")
st.caption("Bring in CVs and jobs manually or from the configured Gmail labels.")

with st.expander("Manual CV upload", expanded=True):
    st.caption("Supported now: text-based PDF, DOCX, and TXT up to 15 MB.")
    uploaded_file = st.file_uploader("Upload a CV", type=["pdf", "docx", "txt"])
    if uploaded_file is not None and st.button("Ingest CV", type="primary"):
        try:
            result = upload_cv(uploaded_file.name, uploaded_file.getvalue())
            st.success("CV ingested.")
            st.json(result)
        except Exception as error:
            st.error(api_error_message(error))

with st.expander("Gmail daily scan", expanded=True):
    st.markdown(
        """
This scans only the configured Gmail labels:

- jobs label from `.env`
- CV/resume label from `.env`

The scan output below shows what labels/messages were found, what attachments were
considered, and whether LLM parsing is enabled.
"""
    )
    if st.button("Scan Gmail now", type="primary"):
        try:
            with st.spinner("Scanning Gmail labels and processing supported messages..."):
                result = post_empty("/ingestion/gmail/daily")

            if not result.get("enabled"):
                st.warning("Gmail ingestion is disabled.")
            else:
                st.success("Gmail scan completed.")

            metric_columns = st.columns(6)
            metric_columns[0].metric("Job emails found", result.get("job_messages_found", 0))
            metric_columns[1].metric("CV emails found", result.get("cv_messages_found", 0))
            metric_columns[2].metric("Jobs drafted", result.get("jobs_drafted", 0))
            metric_columns[3].metric("CVs ingested", result.get("cvs_ingested", 0))
            metric_columns[4].metric("Duplicates skipped", result.get("duplicates_skipped", 0))
            metric_columns[5].metric("Errors", len(result.get("errors", [])))

            st.caption(
                "LLM parsing enabled: "
                f"jobs={result.get('llm_job_parsing_enabled')}, "
                f"CVs={result.get('llm_cv_parsing_enabled')}"
            )

            events = result.get("events") or []
            if events:
                st.subheader("Scan progress")
                st.dataframe(pd.DataFrame(events), hide_index=True, use_container_width=True)

            if result.get("available_labels"):
                with st.expander("Gmail labels seen by the app"):
                    st.write(result["available_labels"])

            if result.get("errors"):
                st.error("Some items failed during scan.")
                st.json(result["errors"])

            with st.expander("Raw scan result"):
                st.json(result)
        except Exception as error:
            st.error(api_error_message(error))
