"""
Simple Counter Example

This example demonstrates the most basic usage of `st_page_state` to manage
a single integer state variable. It shows how to:
1. Define a PageState class.
2. Declare a StateVar with a default value.
3. Read and modify the state variable directly.
4. Reset the state variable to its default value.
"""

import streamlit as st
from st_page_state import PageState, StateVar

st.set_page_config(page_title="Simple Counter Example")

class CounterState(PageState):
    """
    Define the state for this page.
    Inheriting from PageState automatically handles session state persistence.
    """
    # Define a single integer variable initialized to 0.
    count: int = StateVar(default=0)

st.title("Simple Counter")
st.markdown(
    """
    This example demonstrates the simplest usage of `st_page_state`.
    The count value persists across reruns.
    """
)

# Access the state variable directly using the class attribute.
st.metric(label="Current Count", value=CounterState.count)

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("Increment", width="stretch"):
        # Directly modify the state variable like a normal property.
        CounterState.count += 1
        st.rerun()

with col2:
    if st.button("Decrement", width="stretch"):
        CounterState.count -= 1
        st.rerun()

with col3:
    if st.button("Reset", type="primary", width="stretch"):
        # Reset specific field to its default value.
        CounterState.reset("count")
        st.rerun()
