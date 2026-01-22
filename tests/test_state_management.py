import pytest
from st_page_state import PageState, StateVar
import streamlit as st

class TestStateManagement:
    """Tests for basic state management functionality (get, set, reset, dump)."""

    def test_basic_state_initialization(self):
        """Test that state variables initialize with default values."""
        class CounterState(PageState):
            count: int = StateVar(default=10)

        # Test default value
        assert CounterState.count == 10
        
    def test_state_update(self):
        """Test that updating a state variable reflects in the class and session state."""
        class CounterState(PageState):
            count: int = StateVar(default=10)

        # Test update
        CounterState.count = 20
        assert CounterState.count == 20
        
        # Test session state persistence
        # Note: internal structure relies on SESSION_STATE_KEY = "_st_page_state"
        assert st.session_state["_st_page_state"]["CounterState"]["count"] == 20

    def test_reset_state(self):
        """Test that reset() restores variables to their default values."""
        class FormState(PageState):
            name: str = StateVar(default="")
        
        FormState.name = "John"
        assert FormState.name == "John"
        
        FormState.reset()
        assert FormState.name == ""

    def test_dump_state(self):
        """Test that dump() returns a dictionary of current state values."""
        class DumpState(PageState):
            a: int = StateVar(default=1)
            b: int = StateVar(default=2)
            
        # Trigger initialization by accessing attributes
        _ = DumpState.a
        _ = DumpState.b
        
        dump = DumpState.dump()
        assert dump == {"a": 1, "b": 2}
