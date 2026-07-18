import pandas as pd
import streamlit as st


COLUMN_LABELS = {
    "id": "מזהה",
    "full_name": "שם מלא",
    "email": "דוא״ל",
    "phone": "טלפון",
    "city": "עיר",
    "country": "מדינה",
    "current_title": "תפקיד נוכחי",
    "seniority": "ותק",
    "total_years_experience": "שנות ניסיון",
    "status": "סטטוס",
    "ai_summary": "תקציר",
    "client_name": "לקוח",
    "title": "כותרת",
    "location": "מיקום",
    "min_years_experience": "מינימום שנות ניסיון",
    "summary": "תקציר",
    "description": "תיאור",
    "candidate_id": "מזהה מועמד",
    "job_id": "מזהה משרה",
    "total_score": "ציון",
    "hard_filter_passed": "עומד בתנאי הסף",
    "explanation": "הסבר",
    "risks": "סיכונים",
    "missing_requirements": "דרישות חסרות",
    "created_at": "נוצר בתאריך",
    "updated_at": "עודכן בתאריך",
    "owner_type": "סוג בעלים",
    "owner_id": "מזהה בעלים",
    "source_type": "סוג מקור",
    "embedding_model": "מודל הטמעה",
    "dimensions": "ממדים",
    "preview_text": "תצוגה מקדימה",
    "source": "מקור",
    "entity_type": "סוג ישות",
    "entity_id": "מזהה ישות",
    "detail": "פרטים",
    "source_label": "תווית מקור",
    "source_message_id": "מזהה הודעה",
    "source_attachment_id": "מזהה קובץ מצורף",
}


def apply_rtl() -> None:
    """Apply consistent Hebrew/right-to-left presentation to every Streamlit page."""
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
        [data-testid="stHeader"], [data-testid="stDataFrame"],
        [data-testid="stDataEditor"] { direction: rtl; }
        [data-testid="stAppViewContainer"] *, [data-testid="stSidebar"] * {
            text-align: right;
        }
        [data-testid="stSidebarNav"] ul { direction: rtl; }
        [data-testid="stSidebarNav"] li a { justify-content: flex-start; }
        input, textarea, [contenteditable="true"] { direction: rtl !important; text-align: right !important; }
        [data-testid="stDataFrame"] [role="columnheader"],
        [data-testid="stDataEditor"] [role="columnheader"] { text-align: right !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hebrew_columns(frame: pd.DataFrame) -> pd.DataFrame:
    translated = frame.rename(
        columns={column: COLUMN_LABELS.get(column, column) for column in frame.columns}
    )
    return translated.loc[:, list(reversed(translated.columns))]
