import pandas as pd
import streamlit as st

from apps.dashboard.api_client import api_error_message, get_json, post_empty

st.set_page_config(page_title="Dev - Vector DB", layout="wide")
st.title("Dev - Vector DB")
st.caption("Local SQLite embedding records used for retrieval before matching.")

if st.button("Rebuild embeddings", type="primary"):
    try:
        st.json(post_empty("/dev/vectors/rebuild"))
    except Exception as error:
        st.error(api_error_message(error))

try:
    rows = get_json("/dev/vectors")
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.info("No vector records yet.")
    else:
        display_columns = [
            "owner_type",
            "owner_id",
            "source_type",
            "embedding_model",
            "dimensions",
            "preview_text",
            "created_at",
            "id",
        ]
        st.dataframe(
            frame[[column for column in display_columns if column in frame]],
            hide_index=True,
            use_container_width=True,
        )
except Exception as error:
    st.error(api_error_message(error))
