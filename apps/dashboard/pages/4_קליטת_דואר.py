import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, post_empty, upload_cv
from apps.dashboard.ui import apply_rtl, hebrew_columns

st.set_page_config(page_title="קליטת דואר", layout="wide")
apply_rtl()
st.title("קליטת קורות חיים ומשרות")
st.caption("אפשר לקלוט קורות חיים ומשרות ידנית או מתוויות Gmail שהוגדרו במערכת.")

with st.expander("העלאת קורות חיים ידנית", expanded=True):
    st.caption("סוגי קבצים נתמכים: PDF טקסטואלי, DOCX ו־TXT, עד 15MB.")
    uploaded_file = st.file_uploader("העלאת קובץ קורות חיים", type=["pdf", "docx", "txt"])
    if uploaded_file is not None and st.button("קליטת קורות החיים", type="primary"):
        try:
            result = upload_cv(uploaded_file.name, uploaded_file.getvalue())
            st.success("קורות החיים נקלטו.")
            st.json(result)
        except Exception as error:
            st.error(api_error_message(error))

with st.expander("סריקה יומית של Gmail", expanded=True):
    st.markdown(
        """
הסריקה כוללת רק את תוויות Gmail שהוגדרו:

- תווית משרות מתוך `.env`
- תווית קורות חיים מתוך `.env`

הפלט שלהלן מציג אילו תוויות והודעות נמצאו, אילו קבצים צורפו, והאם ניתוח AI פעיל.
"""
    )
    if st.button("סריקת Gmail כעת", type="primary"):
        try:
            with st.spinner("סורק תוויות Gmail ומעבד הודעות נתמכות..."):
                result = post_empty("/ingestion/gmail/daily", timeout=1800)

            if not result.get("enabled"):
                st.warning("קליטת Gmail אינה פעילה.")
            else:
                st.success("סריקת Gmail הושלמה.")

            metric_columns = st.columns(6)
            metric_columns[0].metric("הודעות משרה", result.get("job_messages_found", 0))
            metric_columns[1].metric("הודעות קורות חיים", result.get("cv_messages_found", 0))
            metric_columns[2].metric("טיוטות משרה", result.get("jobs_drafted", 0))
            metric_columns[3].metric("קורות חיים שנקלטו", result.get("cvs_ingested", 0))
            metric_columns[4].metric("כפילויות שדולגו", result.get("duplicates_skipped", 0))
            metric_columns[5].metric("שגיאות", len(result.get("errors", [])))

            st.caption(
                "ניתוח AI פעיל: "
                f"משרות={result.get('llm_job_parsing_enabled')}, "
                f"קורות חיים={result.get('llm_cv_parsing_enabled')}"
            )

            events = result.get("events") or []
            if events:
                st.subheader("התקדמות הסריקה")
                st.dataframe(hebrew_columns(pd.DataFrame(events)), hide_index=True, use_container_width=True)

            if result.get("available_labels"):
                with st.expander("תוויות Gmail שזוהו"):
                    st.write(result["available_labels"])

            if result.get("errors"):
                st.error("חלק מהפריטים נכשלו במהלך הסריקה.")
                st.json(result["errors"])

            with st.expander("תוצאת סריקה גולמית"):
                st.json(result)
        except Exception as error:
            st.error(api_error_message(error))
