"""
Data Filter & Mapping Example

This example demonstrates how to use `value_map` to decouple internal state representation
from the public URL representation.

Scenario:
- Internally (in code and database), we use integers (0, 1, 2) for status.
- Externally (in the URL), we want friendly strings ("pending", "active", "archived").
"""

import streamlit as st
from st_page_state import PageState, StateVar
import pandas as pd

st.set_page_config(page_title="Data Filter & Mapping Example")

class FilterState(PageState):
    """
    State class managing the filter selection.
    """
    
    # Map friendly URL strings to internal integer values.
    # The 'value_map' dictionary keys are what appear in the URL.
    # The values are the STRING representation of the internal value.
    status_filter: int = StateVar(
        default=1, # Default is Active (1)
        url_key="status",
        value_map={
            "pending": 0,
            "active": 1,
            "archived": 2
        }
    )

st.title("Data Filter with Value Mapping")
st.markdown("""
This example demonstrates `value_map`.
We work with **integers** (0, 1, 2) in our code, but the URL shows **friendly strings** (pending, active, archived).
""")

# Define what our integers mean for display in the UI
status_labels = {0: "Pending", 1: "Active", 2: "Archived"}

# Controls
col1, col2 = st.columns([1, 2])
with col1:
    st.selectbox(
        "Filter by Status",
        options=[0, 1, 2],
        format_func=lambda x: status_labels[x],
        **FilterState.bind("status_filter")
    )

# Mock Data
data = [
    {"id": 101, "task": "Fix login bug", "status": 1},
    {"id": 102, "task": "Write documentation", "status": 0},
    {"id": 103, "task": "Release v1.0", "status": 2},
    {"id": 104, "task": "Update styles", "status": 1},
    {"id": 105, "task": "User interviews", "status": 0},
]
df = pd.DataFrame(data)

# Filter Logic
filtered_df = df[df["status"] == FilterState.status_filter]

# Display
st.subheader(f"Tasks ({status_labels[FilterState.status_filter]})")
st.dataframe(
    filtered_df,
    column_config={
        "status": st.column_config.NumberColumn(
            "Status Code",
            help="Internal integer representation"
        )
    },
    width="stretch"
)

st.divider()

# Helper to reverse look up the URL string from the current state value
# (Just for display purposes in this example)
def get_url_string(value):
    # Access the mapping directly from the field definition for demonstration
    mapping = FilterState.schema()['status_filter']['value_map']
    for url_str, internal_val_str in mapping.items():
        if internal_val_str == str(value):
            return url_str
    return "unknown"

current_url_val = get_url_string(FilterState.status_filter)

st.info(f"Check the URL! It says `?status={current_url_val}` instead of `?status={FilterState.status_filter}`.")
st.caption(f"Internal State Value: `{FilterState.status_filter}` (type: {type(FilterState.status_filter).__name__})")
