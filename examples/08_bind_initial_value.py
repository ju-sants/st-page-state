"""
Bind with Initial Value Example

This example demonstrates how to provide a custom initial value when binding a widget
to a state variable. This is useful when you want a widget to start with a specific 
value without changing the global `StateVar` default.

Key features shown:
1. Using the `value` parameter in `PageState.bind()`.
2. How the initial value only applies if the state isn't already set in session_state.
3. Contrast between `StateVar(default=...)` and `bind(value=...)`.
"""

import streamlit as st
from st_page_state import PageState, StateVar

st.set_page_config(page_title="Bind Initial Value Example")

class CounterState(PageState):
    """
    Define the state for this page.
    The 'count' variable has a global default of 0.
    """
    count: int = StateVar(default=0)

st.title("Bind with Initial Value")
st.markdown(
    """
    When using `.bind()`, you can pass a `value` argument. 
    This value will be used to initialize the widget **only if it hasn't been set yet** 
    (either by user interaction or by being present in the URL).
    """
)

# Use bind with a custom initial value of 10.
# The StateVar default is 0, but the widget will start at 10 on the first load.
binding = CounterState.bind("count", value=10)

st.number_input("Counter Widget (Starts at 10)", **binding)

st.divider()

st.write(f"**Current PageState.count value:** `{CounterState.count}`")

if st.button("Reset All State", type="primary"):
    # Resetting the state will clear the widget key and return 'count' to its StateVar default (0).
    # On the next run, .bind(value=10) will see the empty state and apply 10 again.
    CounterState.reset()
    st.rerun()
