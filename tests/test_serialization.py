import pytest
from st_page_state.utils.converters import convert_to_URL, convert_from_URL
from typing import List, Dict, Any

class TestURLSerialization:
    """Tests for URL serialization and deserialization logic."""

    @pytest.mark.parametrize("dtype, value", [
        (str, "hello"),
        (int, 123),
        (float, 45.6),
        (bool, True),
        (List[str], ["a", "b", "c"]),
        (List[int], [1, 2, 3]),
        (List[str], ["a||b", "c"]),
    ])

    def test_symmetric_conversion(self, dtype, value):
        """Test that types can be converted to URL and back."""

        encoded = convert_to_URL("test_key", value)
        decoded = convert_from_URL("test_key", encoded, dtype)

        assert decoded == value

    def test_nested_list_is_supported(self):
        """Test that nested lists are correctly serialized and deserialized."""

        value = [[1, 2], [3, 4]]
        dtype = List[List[int]]
        
        encoded = convert_to_URL("test_key", value)
        decoded = convert_from_URL("test_key", encoded, dtype)
        
        assert decoded == value

    def test_value_map_serialization(self):
        """Test serialization with a value_map."""

        value_map = {"internal_1": "url_1", "internal_2": "url_2"}
        encoded = convert_to_URL("test_key", "internal_1", value_map)

        assert encoded == "url_1"

    def test_value_map_deserialization(self):
        """Test deserialization with a value_map."""

        value_map = {"internal_1": "url_1", "internal_2": "url_2"}
        decoded = convert_from_URL("test_key", "url_1", str, value_map)

        assert decoded == "internal_1"

    def test_value_map_precedence(self):
        """Test that value_map takes precedence over standard type conversion."""

        value_map = {1: "one", 2: "two"} # int to string
        encoded = convert_to_URL("test_key", 1, value_map)

        assert encoded == "one"
        
        decoded = convert_from_URL("test_key", "one", int, value_map)

        assert decoded == 1

    def test_value_map_unhashable_value(self):
        """Test that passing an unhashable value (list) with a value_map doesn't crash."""
        
        value_map = {1: "one"}
        value = [1, 2] # List is unhashable
        
        # This check ensures we don't try to look up the entire list in the value_map, which would raise TypeError
        encoded = convert_to_URL("test_key", value, value_map)
        
        assert isinstance(encoded, str)
