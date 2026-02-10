import pytest
from st_page_state import PageState, StateVar
import streamlit as st

class TestWidgetBinding:
    """Tests for widget binding functionality (key generation and callbacks)."""

    def test_binding_structure(self):
        """Test the structure of the dictionary returned by bind()."""
        class BindState(PageState):
            text: str = StateVar(default="hello")

        binding = BindState.bind("text")
        
        # Check structure
        assert "key" in binding
        assert "on_change" in binding
        
        # Key format defined in state.py: f"{cls.__name__}_{field}_widget"
        expected_key = "BindState_text_widget"
        assert binding["key"] == expected_key
        
        # Check initial value set in session state
        assert st.session_state[expected_key] == "hello"

    def test_binding_callback_execution(self):
        """Test that the binding callback updates the class state from the widget value."""
        class CallbackState(PageState):
            value: int = StateVar(default=0)
        
        binding = CallbackState.bind("value")
        callback = binding["on_change"]
        widget_key = binding["key"]
        
        # Simulate widget change (Streamlit does this when user interacts)
        st.session_state[widget_key] = 42
        
        # Call callback (Streamlit calls this)
        callback()
        
        # Verify class state updated
        assert CallbackState.value == 42

    def test_binding_invalid_field_raises_error(self):
        """Test that binding a non-existent field raises a ValueError."""
        class ErrorState(PageState):
            exists: int = StateVar(0)
            
        with pytest.raises(ValueError):
            ErrorState.bind("non_existent")

    def test_binding_with_custom_initial_value(self):
        """Test that passing 'value' to bind sets the initial widget state."""
        class CustomValueState(PageState):
            count: int = StateVar(default=0)
        
        # Bind with a custom value
        binding = CustomValueState.bind("count", value=10)
        widget_key = binding["key"]
        
        # Verify widget session state has the custom value, not the default
        assert st.session_state[widget_key] == 10
        
        # Note: The PageState itself only updates when the callback is called
        # (simulating widget interaction) or if we access it.
        # In current implementation of bind, it doesn't set the PageState attribute immediately,
        # it just sets the widget key in session_state.
        assert CustomValueState.count == 0

    def test_binding_custom_value_does_not_overwrite_existing(self):
        """Test that custom value in bind doesn't overwrite if widget key already exists."""
        class PersistenceState(PageState):
            value: int = StateVar(default=0)
            
        widget_key = "PersistenceState_value_widget"
        st.session_state[widget_key] = 42
        
        # Bind with a DIFFERENT custom value
        PersistenceState.bind("value", value=100)
        
        # Should still be 42, not 100
        assert st.session_state[widget_key] == 42
