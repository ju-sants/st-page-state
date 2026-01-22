"""
Form Section Example

This example demonstrates how to create a settings form where some fields are
persisted in the URL (for bookmarking/sharing) and others are kept only in the
session state.

Key features:
- `url_key`: Maps a state variable to a specific URL query parameter.
- `bind()`: Easily connects Streamlit widgets to state variables.
- `dump()`: Exports the current state as a dictionary.
"""

import streamlit as st
from st_page_state import PageState, StateVar

st.set_page_config(page_title="Form Section Example")

class SettingsState(PageState):
    """
    State for the Settings page.
    """
    # These variables are bound to URL parameters.
    # Changing the widget updates the URL; loading the URL updates the widget.
    username: str = StateVar(default="guest", url_key="user")
    theme: str = StateVar(default="light", url_key="theme")
    notifications: bool = StateVar(default=True, url_key="notify")
    
    # 'bio' is not in the URL (no url_key), but it persists across reruns.
    bio: str = StateVar(default="")

st.title("User Profile Settings")
st.markdown(
    """
    Change the settings below and notice how the URL updates automatically.
    You can refresh the page or share the URL, and your settings (except Bio) will be restored.
    """
)

with st.container(border=True):
    st.subheader("Account Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("Username", **SettingsState.bind("username"))
    
    with col2:
        st.selectbox("Theme Preference", ["light", "dark", "system"], **SettingsState.bind("theme"))

    st.checkbox("Enable Email Notifications", **SettingsState.bind("notifications"))
    
    st.text_area("Short Bio", help="Tell us about yourself", **SettingsState.bind("bio"))

st.divider()
st.subheader("Current State Dump")
st.text("SettingsState.dump() returns a dictionary of all current values:")
st.json(SettingsState.dump())

if st.button("Reset to Defaults", type="primary"):
    SettingsState.reset()
    st.rerun()
