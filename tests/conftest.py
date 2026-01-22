import pytest
import sys
import os
from unittest.mock import MagicMock

# Ensure the src directory is in the path so we can import the package
# This is useful when running tests directly without installing the package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock streamlit before importing anything else from st_page_state
# This is necessary because st_page_state imports streamlit at the top level
mock_st = MagicMock()
mock_st.session_state = {}
mock_st.query_params = {}
sys.modules["streamlit"] = mock_st

@pytest.fixture(autouse=True)
def reset_mock_state():
    """
    Fixture to reset the mock streamlit state before each test.
    This ensures that tests do not interfere with each other via shared session state.
    """
    mock_st.session_state.clear()
    mock_st.query_params.clear()
