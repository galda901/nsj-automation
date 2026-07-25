import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json, patch_json, post_empty, post_json
from apps.dashboard.ui import apply_rtl


STATUS_LABELS = {"draft": "טיוטה", "open": "פתוחה", "closed": "סגורה"}
CANDIDATE_STATUS_LABELS = {
    "new": "חדש",
    "reference_check": "שיחת ממליצים",
    "submitted_to_client": "הועבר ללקוח",
    "interview_passed": "עבר ראיון",
    "awaiting_response": "ממתין לתשובה",
    "not_relevant": "לא רלוונטי",
}
SENIORITY_LABELS = {
    "junior": "ג'וניור",
    "mid": "ביניים",
    "senior": "בכיר",
    "lead": "מוביל",
    "manager": "מנהל",
}
PROCESS_CLOSED_STATUSES = {"closed", "rejected", "withdrawn", "hired"}
NOT_RELEVANT_STATUS = "not_relevant"


def clean_value(value: object) -> object:
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    return value.strip() if isinstance(value, str) else value


def changed_jobs(edited: pd.DataFrame, original: pd.DataFrame) -> list[tuple[str, dict]]:
    field_map = {
        "לקוח": "client_name",
        "שם המשרה": "title",
        "מיקום": "location",
        "ותק": "seniority",
        "מינימום שנות ניסיון": "min_years_experience",
        "סטטוס": "status",
        "תקציר": "summary",
        "תיאור": "description",
    }
    original_by_id = original.set_index("id")
    changes: list[tuple[str, dict]] = []
    for row in edited.to_dict("records"):
        job_id = row["id"]
        before = original_by_id.loc[job_id]
        payload = {
            api_field: (
                {value: key for key, value in STATUS_LABELS.items()}.get(clean_value(row[column]), clean_value(row[column]))
                if api_field == "status"
                else {value: key for key, value in SENIORITY_LABELS.items()}.get(clean_value(row[column]), clean_value(row[column]))
                if api_field == "seniority"
                else clean_value(row[column])
            )
            for column, api_field in field_map.items()
            if clean_value(row[column]) != clean_value(before[column])
        }
        if payload:
            changes.append((job_id, payload))
    return changes


def fallback_summary(description: object) -> str:
    text = " ".join(str(description or "").split())
    return text if len(text) <= 300 else f"{text[:299].rstrip()}…"


def candidates_in_progress_by_job(
    applications: list[dict], candidates: list[dict]
) -> dict[str, str]:
    """Format the active candidate processes for the read-only jobs-table column."""
    candidates_by_id = {candidate["id"]: candidate for candidate in candidates}
    names_by_job: dict[str, list[str]] = {}
    for application in applications:
        job_id = application.get("job_id")
        if not job_id or application.get("status") in PROCESS_CLOSED_STATUSES:
            continue
        candidate = candidates_by_id.get(application.get("candidate_id"))
        if candidate is None or candidate.get("status") == NOT_RELEVANT_STATUS:
            continue
        name = candidate.get("full_name") or "מועמד/ת ללא שם"
        candidate_status = CANDIDATE_STATUS_LABELS.get(
            candidate.get("status"), candidate.get("status")
        )
        names_by_job.setdefault(job_id, []).append(f"{name} · {candidate_status}")
    return {job_id: "\n".join(names) for job_id, names in names_by_job.items()}


st.set_page_config(page_title="משרות", layout="wide")
apply_rtl()
st.title("משרות")
st.caption("אפשר לערוך משרות ישירות בטבלה. משרות שמיובאות מדוא״ל מתחילות כטיוטות.")

try:
    jobs = get_json("/jobs")
    applications = get_json("/applications")
    candidates = get_json("/candidates")
    frame = pd.DataFrame(jobs)
    if frame.empty:
        st.info("עדיין אין משרות. אפשר ליצור משרה חדשה בטופס למטה.")
    else:
        candidates_in_progress = candidates_in_progress_by_job(applications, candidates)
        view = pd.DataFrame(
            {
                "תיאור": frame["description"],
                "תקציר": frame.get("summary", frame["description"].map(fallback_summary)),
                "מועמדים בתהליך": frame["id"].map(candidates_in_progress).fillna(""),
                "סטטוס": frame["status"].map(lambda value: STATUS_LABELS.get(value, value)),
                "מינימום שנות ניסיון": frame["min_years_experience"],
                "ותק": frame["seniority"].map(lambda value: SENIORITY_LABELS.get(value, value)),
                "מיקום": frame["location"],
                "שם המשרה": frame["title"],
                "לקוח": frame["client_name"],
                "id": frame["id"],
            }
        )
        edited = st.data_editor(
            view,
            hide_index=True,
            use_container_width=True,
            key="job-editor",
            disabled=["מועמדים בתהליך"],
            column_config={
                "id": None,
                "מועמדים בתהליך": st.column_config.TextColumn(width="medium"),
                "מינימום שנות ניסיון": st.column_config.NumberColumn(min_value=0.0, step=0.5),
                "סטטוס": st.column_config.SelectboxColumn(options=list(STATUS_LABELS.values())),
                "ותק": st.column_config.SelectboxColumn(options=list(SENIORITY_LABELS.values())),
                "תקציר": st.column_config.TextColumn(width="large"),
                "תיאור": st.column_config.TextColumn(width="large"),
            },
        )
        if st.button("שמירת שינויים במשרות", type="primary"):
            changes = changed_jobs(edited, view)
            if not changes:
                st.info("אין שינויים במשרות לשמירה.")
            else:
                try:
                    for job_id, payload in changes:
                        patch_json(f"/jobs/{job_id}", payload)
                    st.success(f"נשמרו שינויים ב־{len(changes)} משרות.")
                    st.rerun()
                except Exception as error:
                    st.error(api_error_message(error))
        draft_jobs = [job for job in jobs if job.get("status") == "draft"]
        if draft_jobs:
            st.divider()
            st.subheader("סקירת טיוטות")
            options = {
                f"{job['title']} — {job['client_name']} ({job['id']})": job["id"]
                for job in draft_jobs
            }
            selected = st.selectbox("בחירת טיוטה לפתיחה", list(options))
            if st.button("פתיחת המשרה שנבחרה"):
                try:
                    opened = post_empty(f"/jobs/{options[selected]}/open")
                    st.success(f"המשרה נפתחה: {opened['title']}")
                    st.rerun()
                except Exception as error:
                    st.error(api_error_message(error))
except Exception as error:
    st.error(api_error_message(error))

st.divider()
with st.expander("יצירת משרה חדשה", expanded=True):
    with st.form("create-job", clear_on_submit=True):
        client_name = st.text_input("שם הלקוח")
        title = st.text_input("שם המשרה")
        location = st.text_input("מיקום")
        seniority = st.selectbox(
            "ותק", [""] + list(SENIORITY_LABELS.values())
        )
        min_years = st.number_input("מינימום שנות ניסיון", min_value=0.0, step=0.5)
        description = st.text_area("תיאור המשרה")
        summary = st.text_area("תקציר", help="תקציר קצר אופציונלי לצוות הגיוס.")
        submitted = st.form_submit_button("יצירת משרה", type="primary")
    if submitted:
        if not client_name.strip() or not title.strip() or not description.strip():
            st.error("שם הלקוח, שם המשרה ותיאור המשרה הם שדות חובה.")
        else:
            try:
                created = post_json(
                    "/jobs",
                    {
                        "client_name": client_name,
                        "title": title,
                        "location": location or None,
                        "seniority": {value: key for key, value in SENIORITY_LABELS.items()}.get(seniority) or None,
                        "min_years_experience": min_years or None,
                        "description": description,
                        "summary": summary or None,
                    },
                )
                st.success(f"המשרה נוצרה: {created['title']} ({created['id']})")
                st.rerun()
            except Exception as error:
                st.error(api_error_message(error))
