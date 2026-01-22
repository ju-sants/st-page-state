import pytest
from st_page_state import PageState, StateVar
import streamlit as st

class TestConfig:
    """Tests for the Config class functionality."""

    def test_selfish_behavior_on_set(self):
        """Test that `url_selfish=True` removes other query params on set."""
        
        class SelfishPage(PageState):
            class Config:
                url_selfish = True
            
            q: str = StateVar(default="default", url_key="q")
            p: int = StateVar(default=1, url_key="p")

        # Set unrelated query params
        st.query_params["garbage"] = "should_be_gone"
        st.query_params["f"] = "some_filter"
        st.query_params["q"] = "initial"

        # Act: Setting a value on SelfishPage should trigger the cleanup
        SelfishPage.q = "new_value"

        # Assert: Check that only SelfishPage's params remain
        assert st.query_params == {"q": "new_value"}

    def test_selfish_behavior_preserves_own_keys(self):
        """Test that `url_selfish=True` preserves all keys defined in its own class."""
        
        class SelfishPage(PageState):
            class Config:
                url_selfish = True
            
            q: str = StateVar(default="default", url_key="q")
            p: int = StateVar(default=1, url_key="p")

        # Set one of its own keys and a garbage key
        st.query_params["p"] = "5"
        st.query_params["garbage_again"] = "trash"
        
        # Act: Update another of its own keys
        SelfishPage.q = "newer"
        
        # Assert: Both of its keys should be preserved, garbage should be gone
        assert "q" in st.query_params
        assert st.query_params["q"] == "newer"
        assert "p" in st.query_params
        assert st.query_params["p"] == "5"
        assert "garbage_again" not in st.query_params

    def test_selfish_behavior_on_init(self):
        """Test that `url_selfish=True` cleans up URL on lazy initialization."""
        
        class SelfishPageInit(PageState):
            class Config:
                url_selfish = True
            q: str = StateVar(default="def", url_key="q")

        # Set initial params
        st.query_params["garbage"] = "trash"
        st.query_params["q"] = "init_val"
        
        # Act: Accessing the attribute triggers lazy init -> setattr -> sync -> cleanup
        _ = SelfishPageInit.q
        
        # Assert: Garbage is gone, own key remains
        assert st.query_params == {"q": "init_val"}

    def test_url_prefix(self):
        """Test that `url_prefix` is correctly applied to URL keys."""

        class PrefixedPage(PageState):
            class Config:
                url_prefix = "pf_"
            
            foo: str = StateVar(default="bar", url_key="foo")
        
        # Act: Initialize the attribute
        _ = PrefixedPage.foo

        # Assert: The key in the URL should have the prefix
        assert "pf_foo" in st.query_params
        assert st.query_params["pf_foo"] == "bar"
        assert "foo" not in st.query_params
        
    def test_ignore_none_url_true(self):
        """Test that `ignore_none_url=True` (default) removes the key from URL when value is None."""
        
        class NoneIgnoringPage(PageState):
            # Note: ignore_none_url is True by default
            class Config:
                pass
            
            filter: str = StateVar(default="some_filter", url_key="f")

        # Set initial value
        NoneIgnoringPage.filter = "active"
        assert "f" in st.query_params
        
        # Act: Set value to None
        NoneIgnoringPage.filter = None
        
        # Assert: Key should be removed from query params
        assert "f" not in st.query_params
        
    def test_ignore_none_url_false(self):
        """Test that `ignore_none_url=False` keeps the key in URL when value is None."""
        
        class NonePreservingPage(PageState):
            class Config:
                ignore_none_url = False
            
            filter: str = StateVar(default="some_filter", url_key="f")

        # Set initial value
        NonePreservingPage.filter = "active"
        assert "f" in st.query_params
        
        # Act: Set value to None
        NonePreservingPage.filter = None
        
        # Assert: Key should remain in query params
        assert "f" in st.query_params
        assert st.query_params["f"] == ""
