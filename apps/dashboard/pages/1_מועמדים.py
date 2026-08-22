import pandas as pd
import streamlit as st

from apps.dashboard.api_client import (
    API_BASE_URL,
    api_error_message,
    delete_json,
    get_json,
    patch_json,
)
from apps.dashboard.ui import apply_rtl


STATUS_LABELS = {
    "new": "חדש",
    "reference_check": "שיחת ממליצים",
    "submitted_to_client": "הועבר ללקוח",
    "interview_passed": "עבר ראיון",
    "awaiting_response": "ממתין לתשובה",
    "not_relevant": "לא רלוונטי",
}


def clean_value(value: object) -> object:
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    return value.strip() if isinstance(value, str) else value


def changed_candidates(
    edited: pd.DataFrame,
    original: pd.DataFrame,
    job_id_by_label: dict[str, str | None],
) -> list[tuple[str, dict]]:
    field_map = {
        "הערות": "comments",
        "דוא״ל": "email",
        "טלפון": "phone",
        "עיר": "city",
        "תפקיד": "current_title",
        "סטטוס": "status",
        "משרה": "current_job_id",
        "תקציר": "ai_summary",
    }
    original_by_id = original.set_index("id")
    changes: list[tuple[str, dict]] = []
    for row in edited.to_dict("records"):
        candidate_id = row["id"]
        before = original_by_id.loc[candidate_id]
        payload = {
            api_field: (
                {value: key for key, value in STATUS_LABELS.items()}.get(
                    clean_value(row[column]), clean_value(row[column])
                )
                if api_field == "status"
                else job_id_by_label.get(clean_value(row[column]) or "")
                if api_field == "current_job_id"
                else clean_value(row[column])
            )
            for column, api_field in field_map.items()
            if clean_value(row[column]) != clean_value(before[column])
        }
        if payload:
            changes.append((candidate_id, payload))
    return changes


def filter_visible_candidates(view: pd.DataFrame, query: str) -> pd.DataFrame:
    term = query.strip()
    if not term:
        return view
    searchable = view.drop(columns=["id"], errors="ignore").fillna("")
    matches = searchable.astype(str).apply(
        lambda column: column.str.contains(term, case=False, regex=False)
    )
    return view.loc[matches.any(axis=1)]


def candidate_name_link(candidate: pd.Series) -> str:
    """Keep every name renderable by LinkColumn, including candidates without a CV."""
    name = str(candidate.get("full_name") or "")
    if candidate.get("latest_cv_path"):
        return f"{API_BASE_URL}/candidates/{candidate['id']}/latest-cv/open#{name}"
    return f"#{name}"


st.set_page_config(page_title="מועמדים", layout="wide")
apply_rtl()
st.title("מועמדים")
st.caption("תצוגה נוחה לעבודה יומית בגיוס. השדות הטכניים מוסתרים.")
try:
    summary_candidates = get_json("/candidates")
    summary_columns = st.columns(len(STATUS_LABELS) + 1)
    summary_columns[0].metric("סה״כ מועמדים", len(summary_candidates))
    candidate_statuses = pd.Series(
        [candidate.get("status") for candidate in summary_candidates]
    )
    for column, (status, label) in zip(summary_columns[1:], STATUS_LABELS.items()):
        column.metric(label, int((candidate_statuses == status).sum()))
except Exception as error:
    st.error(api_error_message(error))
    st.stop()

left, right = st.columns(2)
q = left.text_input("חיפוש", placeholder="שם, דוא״ל, תפקיד או טקסט מקורות החיים")
candidate_status = right.selectbox(
    "סטטוס",
    [""] + list(STATUS_LABELS),
    format_func=lambda value: STATUS_LABELS.get(value, "הכול"),
)

try:
    jobs = get_json("/jobs")
    job_label_by_id = {
        job["id"]: f"{job['title']} — {job['client_name']} ({job['id']})"
        for job in jobs
    }
    job_id_by_label = {label: job_id for job_id, label in job_label_by_id.items()}
    job_id_by_label[""] = None
    candidates = get_json(
        "/candidates/with-files",
        params={"candidate_status": candidate_status or None},
    )
    frame = pd.DataFrame(candidates)
    if frame.empty:
        st.info("עדיין אין מועמדים. אפשר להעלות קורות חיים בעמוד קליטת דואר.")
    else:
        current_job_ids = frame.get(
            "current_job_id", pd.Series(index=frame.index, dtype="object")
        )
        view = pd.DataFrame(
            {
                "הערות": frame["comments"],
                "תקציר": frame["ai_summary"],
                "נקלט בתאריך": pd.to_datetime(frame["created_at"]).dt.strftime(
                    "%d/%m/%Y %H:%M"
                ),
                "סטטוס": frame["status"].map(
                    lambda value: STATUS_LABELS.get(value, value)
                ),
                "משרה": current_job_ids.map(job_label_by_id).fillna(""),
                "תפקיד": frame["current_title"],
                "עיר": frame["city"],
                "טלפון": frame["phone"],
                "דוא״ל": frame["email"],
                "מחיקה": False,
                "id": frame["id"],
                "שם": frame.apply(candidate_name_link, axis=1),
            }
        )
        st.caption("אפשר לערוך תא ולשמור את השינויים ישירות למסד הנתונים.")
        view = filter_visible_candidates(view, q)
        if view.empty:
            st.info("לא נמצאו מועמדים התואמים לחיפוש.")
        edited = st.data_editor(
            view,
            hide_index=True,
            use_container_width=True,
            key="candidate-editor",
            column_order=[
                "id",
                "מחיקה",
                "הערות",
                "תקציר",
                "נקלט בתאריך",
                "דוא״ל",
                "טלפון",
                "עיר",
                "תפקיד",
                "משרה",
                "סטטוס",
                "שם",
            ],
            disabled=["נקלט בתאריך", "שם"],
            column_config={
                "id": None,
                "מחיקה": st.column_config.CheckboxColumn(
                    "מחיקה", help="סמנו מועמד/ת למחיקה לצמיתות", alignment="right"
                ),
                "נקלט בתאריך": st.column_config.TextColumn(
                    width="small", alignment="right"
                ),
                "שם": st.column_config.LinkColumn(
                    "שם", width="medium", display_text=r"#(.*)", alignment="right"
                ),
                "סטטוס": st.column_config.SelectboxColumn(
                    options=list(STATUS_LABELS.values())
                ),
                "משרה": st.column_config.SelectboxColumn(
                    options=[""] + [label for label in job_id_by_label if label],
                    width="medium",
                ),
                "תפקיד": st.column_config.TextColumn(alignment="right"),
                "עיר": st.column_config.TextColumn(alignment="right"),
                "טלפון": st.column_config.TextColumn(alignment="right"),
                "דוא״ל": st.column_config.TextColumn(alignment="right"),
                "תקציר": st.column_config.TextColumn(
                    width="large", alignment="right"
                ),
                "הערות": st.column_config.TextColumn(
                    width="medium", alignment="right"
                ),
            },
        )
        if st.button("שמירת שינויים במועמדים", type="primary"):
            changes = changed_candidates(edited, view, job_id_by_label)
            if not changes:
                st.info("אין שינויים במועמדים לשמירה.")
            else:
                try:
                    for candidate_id, payload in changes:
                        patch_json(f"/candidates/{candidate_id}", payload)
                    st.success(f"נשמרו שינויים ב־{len(changes)} מועמדים.")
                    st.rerun()
                except Exception as error:
                    st.error(api_error_message(error))
        selected_candidate_ids = edited.loc[
            edited["מחיקה"].fillna(False).astype(bool), "id"
        ].tolist()
        if selected_candidate_ids:
            candidate_names = frame.set_index("id")["full_name"].to_dict()
            selected_names = ", ".join(
                str(candidate_names.get(candidate_id, candidate_id))
                for candidate_id in selected_candidate_ids
            )
            st.warning(f"המחיקה לצמיתות תסיר גם את הנתונים המקושרים: {selected_names}")
            confirmation_key = (
                f"candidate-delete-confirmation-{','.join(selected_candidate_ids)}"
            )
            confirmed = st.checkbox(
                "אני מאשר/ת את המחיקה לצמיתות",
                key=confirmation_key,
            )
            if st.button(
                "מחיקת מועמדים מסומנים",
                type="secondary",
                disabled=not confirmed,
            ):
                try:
                    for candidate_id in selected_candidate_ids:
                        delete_json(f"/candidates/{candidate_id}")
                    st.success(f"נמחקו {len(selected_candidate_ids)} מועמדים.")
                    st.rerun()
                except Exception as error:
                    st.error(api_error_message(error))
except Exception as error:
    st.error(api_error_message(error))
