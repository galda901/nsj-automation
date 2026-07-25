import pandas as pd
import streamlit as st

from apps.dashboard.api_client import (
    API_BASE_URL,
    api_error_message,
    get_json,
    patch_json,
    post_empty,
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


def changed_candidates(edited: pd.DataFrame, original: pd.DataFrame) -> list[tuple[str, dict]]:
    field_map = {
        "הערות": "comments",
        "שם": "full_name",
        "דוא״ל": "email",
        "טלפון": "phone",
        "עיר": "city",
        "תפקיד": "current_title",
        "סטטוס": "status",
        "תקציר": "ai_summary",
    }
    original_by_id = original.set_index("id")
    changes: list[tuple[str, dict]] = []
    for row in edited.to_dict("records"):
        candidate_id = row["id"]
        before = original_by_id.loc[candidate_id]
        payload = {
            api_field: (
                {value: key for key, value in STATUS_LABELS.items()}.get(clean_value(row[column]), clean_value(row[column]))
                if api_field == "status"
                else clean_value(row[column])
            )
            for column, api_field in field_map.items()
            if clean_value(row[column]) != clean_value(before[column])
        }
        if payload:
            changes.append((candidate_id, payload))
    return changes

st.set_page_config(page_title="מועמדים", layout="wide")
apply_rtl()
st.title("מועמדים")
st.caption("תצוגה נוחה לעבודה יומית בגיוס. השדות הטכניים מוסתרים.")
left, right = st.columns(2)
q = left.text_input("חיפוש", placeholder="שם, דוא״ל, תפקיד או טקסט מקורות החיים")
candidate_status = right.selectbox(
    "סטטוס",
    [""] + list(STATUS_LABELS),
    format_func=lambda value: STATUS_LABELS.get(value, "הכול"),
)

try:
    candidates = get_json(
        "/candidates/with-files",
        params={"q": q or None, "candidate_status": candidate_status or None},
    )
    frame = pd.DataFrame(candidates)
    if frame.empty:
        st.info("עדיין אין מועמדים. אפשר להעלות קורות חיים בעמוד קליטת דואר.")
    else:
        view = pd.DataFrame(
            {
                "הערות": frame["comments"],
                "תקציר": frame["ai_summary"],
                "סטטוס": frame["status"].map(lambda value: STATUS_LABELS.get(value, value)),
                "תפקיד": frame["current_title"],
                "עיר": frame["city"],
                "טלפון": frame["phone"],
                "דוא״ל": frame["email"],
                "שם": frame["full_name"],
                "id": frame["id"],
            }
        )
        st.caption("אפשר לערוך תא ולשמור את השינויים ישירות למסד הנתונים.")
        edited = st.data_editor(
            view,
            hide_index=True,
            use_container_width=True,
            key="candidate-editor",
            column_config={
                "id": None,
                "סטטוס": st.column_config.SelectboxColumn(
                    options=list(STATUS_LABELS.values())
                ),
                "תקציר": st.column_config.TextColumn(width="large"),
                "הערות": st.column_config.TextColumn(width="medium"),
            },
        )
        if st.button("שמירת שינויים במועמדים", type="primary"):
            changes = changed_candidates(edited, view)
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
        st.divider()
        options = {
            f"{row.get('full_name') or 'מועמד'} ({row.get('email') or row.get('id')})": row
            for row in candidates
        }
        selected = st.selectbox("פתיחה או הורדה של קורות חיים", list(options))
        selected_row = options[selected]
        candidate_id = selected_row["id"]
        if selected_row.get("latest_cv_path"):
            st.code(selected_row["latest_cv_path"], language=None)
            col1, col2, col3 = st.columns(3)
            if col1.button("פתיחת קורות החיים במחשב", type="primary"):
                try:
                    result = post_empty(f"/candidates/{candidate_id}/latest-cv/open")
                    if result.get("opened"):
                        st.success("קורות החיים נפתחו.")
                    else:
                        st.info(result.get("detail", "Open action did not run."))
                except Exception as error:
                    st.error(api_error_message(error))
            col2.link_button(
                "הורדת קורות חיים",
                f"{API_BASE_URL}/candidates/{candidate_id}/latest-cv/download",
            )
            if col3.button("ריענון פרטים עם AI"):
                try:
                    post_empty(f"/candidates/{candidate_id}/refresh-ai")
                    st.success("פרטי המועמד והתקציר עודכנו באמצעות AI.")
                    st.rerun()
                except Exception as error:
                    st.error(api_error_message(error))
        else:
            st.info("למועמד זה עדיין אין קובץ קורות חיים מקושר.")
except Exception as error:
    st.error(api_error_message(error))
