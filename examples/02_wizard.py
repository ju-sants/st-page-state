"""
Wizard Example

This example demonstrates how to build a multi-step wizard application.
It highlights:
1. syncing the current step to the URL so users can bookmark or share a specific step.
2. storing form data in session state (without cluttering the URL).
3. validatating data between steps.
"""

import streamlit as st
from st_page_state import PageState, StateVar

st.set_page_config(page_title="Wizard Example")

class WizardState(PageState):
    """
    State management for the Wizard app.
    """
    # 'step' is synced to the URL query parameter 'step'.
    # This allows users to share a link to a specific step (e.g., ?step=2).
    step: int = StateVar(default=1, url_key="step")
    
    # These fields are stored in session state but NOT shown in the URL.
    # This keeps the URL clean and prevents sensitive or bulky data from being exposed.
    name: str = StateVar(default="")
    email: str = StateVar(default="")
    role: str = StateVar(default="Developer")
    agreement: bool = StateVar(default=False)

st.title("Onboarding Wizard")

# Progress bar based on total steps (4)
st.progress(WizardState.step / 4)

if WizardState.step == 1:
    st.subheader("Step 1: Personal Info")
    
    # Bind widgets directly to state variables.
    # The ** operator unpacks the binding dictionary (value, on_change, key) into the widget.
    st.text_input("Full Name", **WizardState.bind("name"))
    st.text_input("Email Address", **WizardState.bind("email"))
    
    if st.button("Next", type="primary"):
        # Simple validation
        if WizardState.name and WizardState.email:
            WizardState.step += 1
            st.rerun()
        else:
            st.error("Please fill in all fields.")

elif WizardState.step == 2:
    st.subheader("Step 2: Role Selection")
    
    roles = ["Developer", "Designer", "Product Manager", "Data Scientist"]
    st.selectbox("Select your role", options=roles, **WizardState.bind("role"))
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Back", width="stretch"):
            WizardState.step -= 1
            st.rerun()
    with col2:
        if st.button("Next", type="primary", width="stretch"):
            WizardState.step += 1
            st.rerun()

elif WizardState.step == 3:
    st.subheader("Step 3: Terms and Conditions")
    
    st.markdown("Please read and accept our terms...")
    st.checkbox("I agree to the terms", **WizardState.bind("agreement"))
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Back", width="stretch"):
            WizardState.step -= 1
            st.rerun()
    with col2:
        if st.button("Next", type="primary", width="stretch"):
            if WizardState.agreement:
                WizardState.step += 1
                st.rerun()
            else:
                st.error("You must agree to the terms.")

elif WizardState.step == 4:
    st.subheader("Step 4: Summary")
    st.success("Registration Complete!")
    
    st.json({
        "Name": WizardState.name,
        "Email": WizardState.email,
        "Role": WizardState.role,
        "Agreed": WizardState.agreement
    })
    
    if st.button("Start Over", type="primary"):
        WizardState.reset() # Resets all fields to their defaults
        st.rerun()
