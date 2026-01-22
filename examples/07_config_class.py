"""
Config Class Example

This example demonstrates how to use the `Config` inner class to modify the behavior
of URL synchronization for a `PageState` model.

The `Config` class allows you to set:
- `url_prefix`: A prefix for all URL query parameters managed by this state.
- `url_selfish`: If `True` (default), removes any URL parameters not managed by this state.
- `ignore_none_url`: If `True` (default), `None` values are not written to the URL.
- `restore_url_on_touch`: If `True` (default), ensures all URL params for a class are present, restoring any that are manually removed or cleared by other selfish states.
"""

import streamlit as st
from st_page_state import PageState, StateVar

st.set_page_config(page_title="Config Class Example")

# ---
# State with URL Prefix
# ---
class PrefixedState(PageState):
    """
    This state class uses a URL prefix 'p1_' for all its parameters.
    It inherits default behaviors: selfish=True, restore_url_on_touch=True.
    """
    
    class Config:
        url_prefix = "p1_"
        # url_selfish = True  <-- Default
        # restore_url_on_touch = True <-- Default

    name: str = StateVar(default="prefixed", url_key="name")
    value: int = StateVar(default=100, url_key="val")

# ---
# Another state without prefix
# ---
class AnotherState(PageState):
    """
    This state uses all defaults (Selfish + Restore).
    """
    other: str = StateVar(default="unprefixed", url_key="other")

# ---
# Explicitly configured state
# ---
class AppState(PageState):
    """
    This state explicitly sets configs for demonstration,
    matching the default values.
    """
    class Config:
        url_selfish = True
        restore_url_on_touch = True

    filter: str = StateVar(default="all", url_key="filter")
    page: int = StateVar(default=1, url_key="page")

# ---
# State sharing URL with another
# ---
class SharedState(PageState):
    """
    This state is selfish but explicitly shares the URL with `PrefixedState`.
    """
    class Config:
        share_url_with = ["PrefixedState"]

    extra: str = StateVar(default="extra", url_key="extra")


st.title("`Config` Class Demonstration")

st.markdown("""
This example shows how the `Config` inner class can control URL behavior.
By default, states are **Selfish** (they clear other URL params) and **Restoring** (they restore their own params if missing).
""")

# Initialize both states to see initial URL
prefixed_name = PrefixedState.name
prefixed_value = PrefixedState.value
another_value = AnotherState.other
app_filter = AppState.filter
app_page = AppState.page
shared_extra = SharedState.extra

st.subheader("1. Prefixed State (Default Behavior)")
st.markdown("Changes to these widgets will update URL params with the prefix `p1_`.")
st.markdown("Because `url_selfish=True` (default), it will also **remove** other parameters (like `?other=...`).")

st.text_input("Name (Prefixed)", **PrefixedState.bind("name"))
st.number_input("Value (Prefixed)", **PrefixedState.bind("value"))

st.caption(f"Current values: `name`='{PrefixedState.name}', `value`={PrefixedState.value}")


st.divider()


st.subheader("2. Standard State (Default Behavior)")
st.markdown("Changes here will set the `?other=...` parameter.")
st.markdown("Because it is also Selfish by default, it will clear the `p1_...` parameters from above.")
st.markdown("However, thanks to `restore_url_on_touch=True` (default), if you go back and touch the Prefixed State widgets, those parameters will come back!")

st.text_input("Other Value (No Prefix)", **AnotherState.bind("other"))

st.caption(f"Current value: `other`='{AnotherState.other}'")

st.divider()

st.info("Check your browser's URL bar to see how the query parameters change!")


st.divider()


st.subheader("3. Third State (Competing Selfishness)")
st.markdown("""
`AppState` is another independent state.

When you interact with this state, it will wipe out both `p1_` parameters and `?other`.
This demonstrates how multiple independent states can coexist: they "fight" for the URL focus, ensuring the URL is always clean and relevant to the most recently touched component.
""")

st.selectbox("Filter", ["all", "active", "completed"], key=AppState.bind_key("filter"))
st.number_input("Page", **AppState.bind("page"))

st.caption(f"Current values: `filter`='{AppState.filter}', `page`={AppState.page}")


st.divider()


st.subheader("4. Shared URL State")
st.markdown("""
`SharedState` is configured with `share_url_with = ["PrefixedState"]`.

When you interact with this state, it will preserve the `p1_` parameters (from `PrefixedState`), even though it is selfish by default.
""")

st.text_input("Extra Info", **SharedState.bind("extra"))
st.caption(f"Current value: `extra`='{SharedState.extra}'")
