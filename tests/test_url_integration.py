import pytest
from st_page_state import PageState, StateVar
import streamlit as st

class TestUrlIntegration:
    """Tests for URL synchronization and initialization."""

    def test_url_sync_on_update(self):
        """Test that updating a state variable updates the URL query parameters."""
        class UrlState(PageState):
            q: str = StateVar(default="default", url_key="q")

        # Accessing the variable should sync default to URL
        _ = UrlState.q
        assert st.query_params["q"] == "default"

        # Update should sync to URL
        UrlState.q = "updated"
        assert st.query_params["q"] == "updated"

    def test_init_from_url(self):
        """Test that state variables initialize from existing URL query parameters."""
        # Setup URL before accessing state
        st.query_params["page"] = "5"
        
        class PaginationState(PageState):
            page: int = StateVar(default=1, url_key="page")

        # Should read from URL and convert type
        assert PaginationState.page == 5
        assert isinstance(PaginationState.page, int)

    def test_value_map_logic(self):
        """Test value mapping between URL string values and internal state values."""
        # Setup URL with friendly name
        st.query_params["status"] = "active"
        
        class TaskState(PageState):
            status: int = StateVar(
                default=0, 
                url_key="status",
                value_map={0: "pending", 1: "active"}
            )

        # Should map "active" -> 1 -> int(1)
        assert TaskState.status == 1

        # Test setting value updates URL with friendly name
        TaskState.status = 0
        assert st.query_params["status"] == "pending"
