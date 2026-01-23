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

        # Assert: Check that only SelfishPage's params remain (and p is restored because restore_url_on_touch is True by default)
        assert st.query_params == {"q": "new_value", "p": "1"}

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

    def test_restore_url_on_touch(self):
        """Test that `restore_url_on_touch=True` restores a missing URL param on set."""

        class RestoreUrlPage(PageState):
            class Config:
                restore_url_on_touch = True

            q: str = StateVar(default="default", url_key="q")
            p: int = StateVar(default=1, url_key="p")

        # Initialize both attributes
        RestoreUrlPage.q = "initial_q"
        RestoreUrlPage.p = 10
        assert st.query_params["q"] == "initial_q"
        assert st.query_params["p"] == "10"

        # Manually delete a URL param
        del st.query_params["q"]
        assert "q" not in st.query_params

        # Act: Set another attribute
        RestoreUrlPage.p = 20

        # Assert: The URL for 'q' should be restored from session state
        assert st.query_params["p"] == "20"
        assert "q" in st.query_params
        assert st.query_params["q"] == "initial_q"

    def test_restore_url_on_read(self):
        """Test that `restore_url_on_touch=True` restores URL params on read (getattr)."""

        class RestoreReadPage(PageState):
            # Config defaults are True
            val: str = StateVar(default="init", url_key="val")

        # Init
        RestoreReadPage.val = "saved"
        assert st.query_params["val"] == "saved"

        # Manually delete
        del st.query_params["val"]
        assert "val" not in st.query_params

        # Act: Read the attribute
        _ = RestoreReadPage.val

        # Assert: URL should be restored
        assert st.query_params["val"] == "saved"

    def test_share_url_with(self):
        """Test that `share_url_with` prevents selfish states from clearing shared state params."""
        
        class SharedA(PageState):
            a: str = StateVar(default="val_a", url_key="a")
            
        class SharedB(PageState):
            class Config:
                share_url_with = ["SharedA"] # String name of the class
            
            b: str = StateVar(default="val_b", url_key="b")
            
        # Init A
        SharedA.a = "init_a"
        assert st.query_params["a"] == "init_a"
        
        # Init B
        # By default B is selfish, so it would clear 'a' unless we shared it.
        SharedB.b = "init_b"
        
        assert st.query_params["b"] == "init_b"
        assert st.query_params["a"] == "init_a" # Should persist
        
        # But if we have garbage, it should be gone
        st.query_params["garbage"] = "trash"
        SharedB.b = "update_b"
        
        assert st.query_params["b"] == "update_b"
        assert st.query_params["a"] == "init_a"
        assert "garbage" not in st.query_params

    def test_focus_method(self):
        """Test that the focus() method clears non-class, non-shared URL params."""

        class FocusA(PageState):
            class Config:
                url_selfish = False
                
            a: str = StateVar(default="val_a", url_key="a")

        class FocusB(PageState):
            class Config:
                url_selfish = False
                share_url_with = [FocusA] # Even though not selfish, we share URL with A so when we focus, A's params remain.   

            b: str = StateVar(default="val_b", url_key="b")


        # Set some initial params
        st.query_params["garbage"] = "should_be_removed"
        FocusA.a = "initial_a"
        FocusB.b = "initial_b"

        assert st.query_params == {"garbage": "should_be_removed", "a": "initial_a", "b": "initial_b"}

        # Act: Focus on class B
        FocusB.focus()
        
        # Assert: Garbage should be gone, but A's param should remain due to sharing
        assert "garbage" not in st.query_params
        assert "a" in st.query_params
        assert st.query_params["a"] == "initial_a"
        assert "b" in st.query_params
        assert st.query_params["b"] == "initial_b"
