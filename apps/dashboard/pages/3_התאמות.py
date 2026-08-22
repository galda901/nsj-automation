import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json, post_json
from apps.dashboard.ui import apply_rtl, hebrew_columns


JOB_STATUS_LABELS = {"draft": "טיוטה", "open": "פתוחה"}

st.set_page_config(page_title="התאמות", layout="wide")
apply_rtl()
st.title("התאמות מועמדים")
st.caption("מוצגות התאמות המבוססות על דמיון וקטורי וחישוב מקומי. ההחלטה נשארת בידי המגייס/ת.")

try:
    jobs = [job for job in get_json("/jobs") if job.get("status") != "closed"]
    if not jobs:
        st.info("יש ליצור משרה לפני הפעלת התאמה.")
        st.stop()
    st.caption("אפשר לבצע התאמה גם לטיוטה, לפני פתיחת המשרה לפרסום.")
    options = {
        (
            f"{job['title']} — {job['client_name']} "
            f"[{JOB_STATUS_LABELS.get(job.get('status'), job.get('status'))}]"
        ): job["id"]
        for job in jobs
    }
    selected = st.selectbox("משרה", list(options))
    job_id = options[selected]
    if st.button("הפעלת התאמה", type="primary"):
        result = post_json(f"/matching/jobs/{job_id}/run", {})
        st.success("ההתאמות נבדקו ועודכנו.")
    matches = get_json(f"/matching/jobs/{job_id}")
    frame = pd.DataFrame(matches)
    if frame.empty:
        st.info("עדיין אין תוצאות. יש להפעיל התאמה למשרה זו.")
    else:
        qualified = frame[
            frame["hard_filter_passed"].fillna(False)
            & frame["explanation"].fillna("").str.strip().ne("")
        ].copy()
        if qualified.empty:
            st.info("לא נמצאו מועמדים שעברו את סף ההתאמה למשרה זו.")
            st.stop()
        candidates = get_json("/candidates")
        candidate_by_id = {candidate["id"]: candidate for candidate in candidates}

        def candidate_field(candidate_id: str, field: str) -> object:
            return candidate_by_id.get(candidate_id, {}).get(field)

        view = pd.DataFrame(
            {
                "דרישות להשלמה": qualified["missing_requirements"],
                "נקודות לבדיקה": qualified["risks"],
                "למה זו התאמה טובה": qualified["explanation"],
                "עיר": qualified["candidate_id"].map(
                    lambda candidate_id: candidate_field(candidate_id, "city")
                ),
                "תפקיד": qualified["candidate_id"].map(
                    lambda candidate_id: candidate_field(candidate_id, "current_title")
                ),
                "מועמד/ת": qualified["candidate_id"].map(
                    lambda candidate_id: candidate_field(candidate_id, "full_name")
                    or "מועמד/ת לא מזוהה"
                ),
            }
        )
        st.dataframe(
            hebrew_columns(view),
            hide_index=True,
            use_container_width=True,
            column_config={
                "מועמד/ת": st.column_config.TextColumn(width="medium"),
                "תפקיד": st.column_config.TextColumn(width="medium"),
                "עיר": st.column_config.TextColumn(width="small"),
                "למה זו התאמה טובה": st.column_config.TextColumn(width="large"),
                "נקודות לבדיקה": st.column_config.TextColumn(width="medium"),
                "דרישות להשלמה": st.column_config.TextColumn(width="medium"),
            },
        )
        applications = get_json("/applications")
        active_candidate_ids = {
            application["candidate_id"]
            for application in applications
            if application.get("job_id") == job_id
            and application.get("status") not in {"closed", "rejected", "withdrawn", "hired"}
        }
        available_candidates = {
            f"{candidate_field(candidate_id, 'full_name') or 'מועמד/ת ללא שם'} ({candidate_id})": candidate_id
            for candidate_id in qualified["candidate_id"]
            if candidate_id not in active_candidate_ids
            and candidate_field(candidate_id, "status") != "not_relevant"
        }
        if available_candidates:
            st.divider()
            st.caption("הוספת מועמד/ת לתהליך תקשר אותו למשרה ותציג אותו בעמוד המשרות.")
            candidate_to_add = st.selectbox(
                "מועמד/ת להוספה לתהליך", list(available_candidates)
            )
            if st.button("הוספה לתהליך", type="primary"):
                try:
                    post_json(
                        "/applications",
                        {
                            "candidate_id": available_candidates[candidate_to_add],
                            "job_id": job_id,
                            "source": "matching",
                        },
                    )
                    st.success("המועמד/ת נוספ/ה לתהליך במשרה זו.")
                    st.rerun()
                except Exception as error:
                    st.error(api_error_message(error))
except Exception as error:
    st.error(api_error_message(error))
