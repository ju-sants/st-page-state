"""
Config Class Example

This example demonstrates how to use the `Config` inner class to modify the behavior
of URL synchronization for a `PageState` model.

The `Config` class allows you to set:
- `url_prefix`: A prefix for all URL query parameters managed by this state.
- `url_selfish`: If `True`, removes any URL parameters not managed by this state.
- `ignore_none_url`: If `True` (default), `None` values are not written to the URL.
"""

import streamlit as st
from st_page_state import PageState, StateVar

st.set_page_config(page_title="Config Class Example")

# ---
# State with URL Prefix and Selfish Behavior
# ---
class PrefixedState(PageState):
    """
    This state class uses a URL prefix 'p1_' for all its parameters.
    It is also "selfish", meaning it will clear other URL parameters.
    """
    
    class Config:
        url_prefix = "p1_"
        url_selfish = True

    name: str = StateVar(default="prefixed", url_key="name")
    value: int = StateVar(default=100, url_key="val")

# ---
# Another state without prefix to demonstrate selfishness
# ---
class AnotherState(PageState):
    other: str = StateVar(default="unprefixed", url_key="other")

st.title("`Config` Class Demonstration")

st.markdown("""
This example shows how the `Config` inner class can control URL behavior.
`PrefixedState` uses `url_prefix='p1_'` and `url_selfish=True`.
""")

# Initialize both states to see initial URL
prefixed_name = PrefixedState.name
prefixed_value = PrefixedState.value
another_value = AnotherState.other

st.subheader("1. Prefixed and Selfish State")
st.markdown("Changes to these widgets will update URL params with the prefix `p1_`.")
st.markdown("Because `url_selfish=True`, it will also **remove** the `?other=...` parameter.")

st.text_input("Name (Prefixed)", **PrefixedState.bind("name"))
st.number_input("Value (Prefixed)", **PrefixedState.bind("value"))

st.caption(f"Current values: `name`='{PrefixedState.name}', `value`={PrefixedState.value}")


st.divider()


st.subheader("2. Standard State")
st.markdown("Changes here will set the `?other=...` parameter.")
st.markdown("When you change the prefixed state again, this parameter will disappear.")

st.text_input("Other Value (No Prefix)", **AnotherState.bind("other"))

st.caption(f"Current value: `other`='{AnotherState.other}'")

st.divider()

st.info("Check your browser's URL bar to see how the query parameters change!")
