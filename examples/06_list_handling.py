"""
List Handling Example

This example demonstrates how the framework handles lists and other iterables (sets, tuples).
It supports generic types like `list[int]`, `list[str]`, `list[date]`, etc.

The framework automatically serializes these lists into a compact Base64 encoded JSON string
for the URL, keeping it clean and safe.
"""

import streamlit as st
import datetime
from st_page_state import PageState, StateVar

st.set_page_config(page_title="List Handling Example")

class ListState(PageState):
    """
    State class managing lists of different types.
    """
    
    # List of integers
    # Multiselect returns a list, so this works perfectly with .bind()
    numbers: list[int] = StateVar(
        default=[1, 2, 3],
        url_key="nums"
    )

    # List of strings
    tags: list[str] = StateVar(
        default=["streamlit", "python"],
        url_key="tags"
    )
    
    # Set of dates (unique values)
    # Sets are unordered, but useful for unique selections.
    # Note: We must re-assign the set to trigger the URL update.
    dates: set[datetime.date] = StateVar(
        default={datetime.date.today()},
        url_key="dates"
    )

st.title("List Handling & Serialization")

st.markdown("""
This example shows how `st_page_state` handles lists and other iterables.
Try modifying the values below and check the URL. You'll see a Base64 string representing the list.
""")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. List of Integers")
    
    # We can bind to a multiselect easily
    # Note: multiselect returns a new list on every change, 
    # so the property setter is called and the URL updates automatically.
    st.multiselect(
        "Select Numbers",
        options=[1, 2, 3, 4, 5, 10, 20, 100],
        **ListState.bind("numbers")
    )
    st.caption(f"Current Value: `{ListState.numbers}` (type: `{type(ListState.numbers).__name__}`)")


with col2:
    st.subheader("2. List of Strings")
    
    st.multiselect(
        "Select Tags",
        options=["streamlit", "python", "web", "framework", "state", "management"],
        **ListState.bind("tags")
    )
    st.caption(f"Current Value: `{ListState.tags}` (type: `{type(ListState.tags).__name__}`)")

st.divider()

st.subheader("3. Set of Dates (Mutable Types)")
st.markdown("""
Sets are mutable. If we modify them in place (e.g. `add()`), the property setter isn't triggered.
**We must re-assign the variable** (e.g. `State.var = new_set`) to trigger the URL sync.
""")

# Date input usually returns a single date or a tuple for range.
d = st.date_input("Pick a date to add/remove", datetime.date.today())

c1, c2 = st.columns(2)
if c1.button("Add Date"):
    # 1. Get current set
    current_dates = ListState.dates
    # 2. Modify (create new set to be safe and clean)
    new_dates = set(current_dates)
    new_dates.add(d)
    # 3. Assign back to trigger update
    ListState.dates = new_dates
    st.rerun()

if c2.button("Remove Date"):
    current_dates = ListState.dates
    if d in current_dates:
        new_dates = set(current_dates)
        new_dates.remove(d)
        ListState.dates = new_dates
        st.rerun()

st.write(f"Selected Dates: {sorted(list(ListState.dates))}")

st.divider()

st.info("Check the URL query parameters to see the Base64 encoding!")
