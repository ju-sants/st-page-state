"""
Tabs Navigation Example

This example demonstrates how to use `st_page_state` to control application navigation.
By binding the navigation widget (Radio button in sidebar) to a state variable synced with the URL,
you enable deep linking to specific pages/tabs within your application.
"""

import streamlit as st
from st_page_state import PageState, StateVar
import pandas as pd
import numpy as np

st.set_page_config(page_title="Tabs Navigation Example")

class NavState(PageState):
    """
    Manages the navigation state of the application.
    """
    # 'view' variable controls which "tab" is active.
    # It is synced to the URL, so users can bookmark specific pages.
    view: str = StateVar(default="Dashboard", url_key="view")

# Sidebar Navigation
with st.sidebar:
    st.title("App Navigation")
    # Binding st.radio to state automatically updates the 'view' variable.
    # No manual session_state callbacks needed.
    st.radio(
        "Go to",
        options=["Dashboard", "Data Explorer", "Settings"],
        **NavState.bind("view")
    )

# Main Content Area
if NavState.view == "Dashboard":
    st.title("📊 Dashboard")
    st.write("Welcome to the main dashboard.")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Users", "1,234", "+5%")
    col2.metric("Revenue", "$12,345", "+12%")
    col3.metric("Active Sessions", "56", "-2%")
    
    # Generate some random data for the chart
    chart_data = pd.DataFrame(
        np.random.randn(20, 3),
        columns=['a', 'b', 'c']
    )
    st.line_chart(chart_data)

elif NavState.view == "Data Explorer":
    st.title("💾 Data Explorer")
    st.write("Explore the dataset.")
    
    df = pd.DataFrame(
        np.random.randn(50, 5),
        columns=[f'Col {i}' for i in range(1, 6)]
    )
    st.dataframe(df, width="stretch")

elif NavState.view == "Settings":
    st.title("⚙️ Settings")
    st.write("Application settings go here.")
    st.info(
        "Try copying the URL and opening it in a new tab. "
        "You will land right back on the **Settings** page!"
    )

# Footer
st.markdown("---")
st.caption(f"Current View State: `{NavState.view}`")
