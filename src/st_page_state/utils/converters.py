import datetime
import json
import logging
import base64
from typing import Any, Dict, Type, get_origin, get_args
from collections.abc import Hashable

from ..errors import InvalidQueryParamError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State serialization (used by the Redis backend)
# ---------------------------------------------------------------------------

def _prepare_for_json(obj: Any) -> Any:
    """
    Recursively convert Python objects into JSON-safe, type-tagged form.
    """

    if isinstance(obj, dict):
        return {k: _prepare_for_json(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return {"__type__": "tuple", "__value__": [_prepare_for_json(i) for i in obj]}
    if isinstance(obj, (set, frozenset)):
        return {"__type__": "set", "__value__": [_prepare_for_json(i) for i in obj]}
    if isinstance(obj, list):
        return [_prepare_for_json(i) for i in obj]
    if isinstance(obj, datetime.datetime):
        return {"__type__": "datetime", "__value__": obj.isoformat()}
    if isinstance(obj, datetime.date):
        return {"__type__": "date", "__value__": obj.isoformat()}
    if isinstance(obj, datetime.time):
        return {"__type__": "time", "__value__": obj.isoformat()}
    if isinstance(obj, bytes):
        return {"__type__": "bytes", "__value__": base64.b64encode(obj).decode()}

    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj

    logger.warning(f"skipping non-serializable value of type {type(obj).__name__} (replaced with None)")
    return None


def _state_json_hook(dct: dict) -> Any:
    """``json.loads`` object hook — reconstruct typed objects from their envelope."""

    t = dct.get("__type__")
    if t is None:
        return dct
    
    v = dct["__value__"]
    
    if t == "datetime":
        return datetime.datetime.fromisoformat(v)
    if t == "date":
        return datetime.date.fromisoformat(v)
    if t == "time":
        return datetime.time.fromisoformat(v)
    if t == "set":
        return set(v)
    if t == "tuple":
        return tuple(v)
    if t == "bytes":
        return base64.b64decode(v)
    
    return dct


def serialize_state(data: Dict[str, Any]) -> str:
    """Serialize a state dict to a JSON string for external storage."""
    return json.dumps(_prepare_for_json(data))


def deserialize_state(raw: str) -> Dict[str, Any]:
    """Deserialize a JSON string back into a state dict."""
    return json.loads(raw, object_hook=_state_json_hook)

SEPARATOR = "||"

def convert_from_URL(key: str, value: str, target_type: Type, value_map: dict = None) -> Any:
    """Converts URL string to Python object with error handling."""

    try:

        # ---
        # Value mapping handling.
        # Value map is a way to convert strings to other values before type conversion.
        # e.g.: value_map = {"active": 1, "inactive": 0} will convert "active" to 1 before type conversion.
        if value_map is not None and isinstance(value, Hashable):

            # Reversing the map, so we can map from URL value to internal value
            reverse_map = {v: k for k, v in value_map.items()}

            if value in reverse_map:

                # Convert it
                value = reverse_map[value]

        # ---
        # Type conversion

        # Simple types
        if target_type == bool:
            return value.lower() in ('true', '1', 't', 'yes', 'on')
        if target_type == int:
            return int(value)
        if target_type == float:
            return float(value)
        if target_type == datetime.date:
            return datetime.date.fromisoformat(value)
        if target_type == datetime.datetime:
            return datetime.datetime.fromisoformat(value)
        if target_type == datetime.time:
            return datetime.time.fromisoformat(value)
        
        # ---
        # Iterable types handling
        origin = get_origin(target_type) # If the type is "list[str]" returns "list"

        if origin in (list, tuple, set):

            # Try to decode from Base64 JSON
            try:
                decoded_json = base64.urlsafe_b64decode(value).decode()
                items_str = json.loads(decoded_json)
            
            # Fallback to separator format
            except Exception:
                items_str = [v for v in value.split(SEPARATOR) if v]

            # Default item type
            item_type = str

            # Gets the internal args of a type. If the type is "list[str]" returns "str"
            type_args = get_args(target_type)

            # If there are args, gets the first
            if type_args:
                item_type = type_args[0]
            
            # Recursive call for items
            items_converted = [convert_from_URL(f"{key}[{i}]", item, item_type) for i, item in enumerate(items_str)]
            
            # Try to cast the list to the original iterable type
            if origin == tuple: return tuple(items_converted)
            if origin == set: return set(items_converted)

            # Fallback to list
            return items_converted

        return value # Fallback to string
    
    except Exception as e:

        # Raise package-specific Invalid Query Param Error
        raise InvalidQueryParamError(key, value, target_type, e)
    

def convert_to_URL(key: str, value: Any, value_map: dict = None) -> str:
    """Converts Python object to URL string with error handling."""

    try:

        # ---
        # Type conversion
        
        # Default conversion to string
        converted_value = str(value)

        if isinstance(value, bool):
            converted_value = "true" if value else "false"
        if isinstance(value, (int, float)):
            converted_value = str(value)
        if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
            converted_value = value.isoformat()

        # ---
        # Iterable types handling
        if isinstance(value, (list, tuple, set)):

            # Recursive call for items
            items_str = [convert_to_URL(f"{key}[{i}]", item, value_map) for i, item in enumerate(value)]

            # Serialize to JSON and then to Base64
            json_str = json.dumps(items_str)
            converted_value = base64.urlsafe_b64encode(json_str.encode()).decode()

        # ---
        # Value mapping handling.
        # Value map is a way to convert values to other values.
        # e.g.: value_map = {1: "active", 0: "inactive"} will convert 1 to "active".
        if value_map is not None and isinstance(value, Hashable):
            if value in value_map:
                converted_value = value_map[value]

        # ---
        # Important note: At this time, the converted value is the string representation of the value, or the mapped value.
        # ---

        # Return the converted and/or mapped value
        return converted_value
    
    except Exception as e:

        # Raise package-specific Invalid Query Param Error
        raise InvalidQueryParamError(key, value, str, e)