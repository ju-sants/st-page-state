import streamlit as st
from typing import Any
import copy
import logging

from .var import StateVar
from ..errors import InvalidQueryParamError
from ..utils.converters import convert_from_URL, convert_to_URL

# Basic logger setup
logger = logging.getLogger(__name__)

# Constant for the session state key used to store page state data
SESSION_STATE_KEY = "_st_page_state"

# Registry to track all PageState classes
_PAGE_STATE_REGISTRY = {}

class PageStateMeta(type):
    """
    Metaclass for managing Streamlit session state and URL query parameters.

    This metaclass intercepts class creation to scan for `StateVar` attributes and
    configures the `_model_metadata` dictionary. It overrides `__getattr__` and
    `__setattr__` to redirect attribute access to `st.session_state` and synchronize
    with `st.query_params` if configured.

    Key Features:
    - **State Management**: Automatically handles reading/writing to `st.session_state`.
    - **Declarative Syntax**: Use `StateVar` to define state variables with defaults.
    - **URL Synchronization**: Bidirectional sync between session state and URL query parameters.
    - **Value Mapping**: Map internal values to user-friendly URL string values.

    Example (New Syntax - Preferred):
        class MyPageState(PageStateBase):
            my_attr: str = StateVar(
                default="default_value",
                url_key="my_param",
                value_map={
                    "url_val1": "internal_val1",
                    "url_val2": "internal_val2"
                }
            )

    Example (Legacy Syntax):
        class MyPageState(PageStateBase):
            _model_metadata = {
                "my_attr": "default_value",
                "map_to_url": {
                    "my_attr": "my_param",
                    "value_map": {
                        "my_attr": {
                            "url_val1": "internal_val1",
                            "url_val2": "internal_val2"
                        }
                    }
                }
            }
    """

    def __init__(cls, name, bases, dct):
        """
        Initialize the PageState subclass.

        This method:
        1. Initializes the class using `type`.
        2. Scans for `StateVar` attributes to build `_model_metadata`.
        3. Removes `StateVar` attributes to ensure access triggers `__getattr__`.
        """

        # 1. Calling "type" to initialize the class properly
        super().__init__(name, bases, dct)
        
        # 2. Avoid processing the base class itself
        if name == "PageState": return
        
        # Register the class
        _PAGE_STATE_REGISTRY[name] = cls
        
        # ---
        # 3. Config class Processing
        default_config = {
            "url_selfish": True,
            "url_prefix": "",
            "ignore_none_url": True,
            "restore_url_on_touch": True,
            "share_url_with": [],
        }
        
        # Get user config or use defaults
        user_config = dct.get("Config", None)
        cls._config = default_config.copy()
        
        # Sets it on the class config
        if user_config:
            for key in default_config:
                if hasattr(user_config, key):
                    cls._config[key] = getattr(user_config, key)

        # ---
        # 4. _model_metadata initialization and StateVar scanning

        # Setting a default value to "_model_metadata" if it is not passed already
        if not hasattr(cls, '_model_metadata'):
            cls._model_metadata = {}

        # ---
        # Scan for StateVar attributes
        
        # Iterate over class attributes to find StateVar instances
        for attr_name, attr_value in dct.items():
            if isinstance(attr_value, StateVar):
                
                # Gets the attribute annotation type if exists. This will help on type conversion from URL params.
                if hasattr(cls, '__annotations__') and attr_name in cls.__annotations__:
                    attr_type = cls.__annotations__[attr_name]
                else:
                    # Fallback to the type of the default value, or str if None
                    attr_type = type(attr_value.default) if attr_value.default is not None else str

                # Build this field metadata schema
                cls._model_metadata[attr_name] = {
                    "default": attr_value.default,
                    "url_key": attr_value.url_key,
                    "value_map": attr_value.value_map,
                    "dtype": attr_type
                }
                
                # Remove the StateVar attribute from the class
                # This ensures that accessing Class.Attr triggers PageStateMeta.__getattr__,
                # which handles the state sync logic.
                if hasattr(cls, attr_name):
                    delattr(cls, attr_name)

    # ---
    # Attribute access method, handles: value = Class.attribute
    def __getattr__(cls, key):

        # 1. Avoid recursion: if we are looking for the configuration dict itself,
        # we must not try to access it via getattr again.
        if key == '_model_metadata': raise AttributeError(key)

        # If the attribute is defined as a state attribute
        if key in getattr(cls, '_model_metadata', {}):
            
            # ---
            # 2. Getting the attribute from session state

            # Ensuring the system and class namespaces on session state are defined
            cls._ensure_storage()
            
            # Getting the class namespace on session state
            class_ns = st.session_state[SESSION_STATE_KEY][cls.__name__]

            # If the attribute is already in session state, return it
            if key in class_ns:
                
                # 3. "Restore URL on touch" feature
                if cls._config.get("restore_url_on_touch"):
                    cls._restore_url()
                    
                return class_ns[key]
            
            # 4. Else not in session state, we'll lazy initialize it (retrieve from URL or default value)
            return cls._initialize_attribute(key)
        
        # If the attribute are not in the memory of the class and not in session state, raise a AttributeError
        raise AttributeError(f"'{cls.__name__}' object has no attribute '{key}'")
    
    # Attribute setting method, handles: Class.attribute = value
    def __setattr__(cls, key, value):

        # 1. Avoid recursion when initializing the configuration dict
        if key == '_model_metadata':
            super().__setattr__(key, value)
            return

        # If the attribute is defined as a state attribute
        if key in getattr(cls, '_model_metadata', []):
            
            # ---
            # 2. Setting the attribute on session state

            # Ensuring the system and class namespaces on session state are defined
            cls._ensure_storage()
            
            # Getting the class namespace on session state
            class_ns = st.session_state[SESSION_STATE_KEY][cls.__name__]

            # Hook: If the child class has "before_set" method, calls it
            if hasattr(cls, "before_set"):
                cls.before_set()

            # Getting the old value, to use later on "on_change" hook
            old_value = class_ns.get(key)

            # Setting the value directly on the class session state namespace
            class_ns[key] = value
            
            # ---
            # 3. Url Syncing
            cls._sync_url(key, value)

            # ---
            # 4. "Restore URL on touch" feature
            if cls._config.get("restore_url_on_touch"):
                cls._restore_url()

            # ---
            # Hook: If the child class has "on_change" method, calls it
            if old_value and old_value != value and hasattr(cls, "on_change"):
                cls.on_change(key, old_value, value)

        else:
            # If it is not defined as a session state attribute, we call "type" to initialize it on memory
            super().__setattr__(key, value)

    # ---
    # Internals

    def _ensure_storage(cls):

        # Ensure the system namespace on session state are defined
        if SESSION_STATE_KEY not in st.session_state:
            st.session_state[SESSION_STATE_KEY] = {}

        # Ensure the class namespace on session state are defined
        if cls.__name__ not in st.session_state[SESSION_STATE_KEY]:
            st.session_state[SESSION_STATE_KEY][cls.__name__] = {}

            # Hook: if the child class has an "on_init" method, calls it.
            if hasattr(cls, 'on_init'):
                cls.on_init()

    def _initialize_attribute(cls, field: str) -> Any:
        """
        Lazy initialization of a state attribute.
        Tries to load from URL query params, otherwise uses default.
        Sets the result in state (via __setattr__) to persist it.
        """

        # Extracts the field metadata
        metadata = cls._model_metadata.get(field)
        
        url_key = metadata.get("url_key")
        value_map = metadata.get("value_map")
        default = metadata.get("default")
        dtype = metadata.get("dtype")

        # ---
        # First declaring of the final value to set on state for this attribute
        final_value = None
        
        # Try to load from URL Query Params
        if url_key and url_key in st.query_params:

            # Gets the string value returned from the URL
            url_value = st.query_params[url_key]
            
            try:
                # Convert from URL string to internal Python object
                final_value = convert_from_URL(field, url_value, dtype, value_map)

            except InvalidQueryParamError as invalid_qp:
                logger.error(
                    f"There was an error parsing the URL-value '{url_value}' from URL-key '{url_key}' of the state attribute '{field}'." \
                    f"Falling back to default value '{default}'. Error: {invalid_qp}"
                )
            
        # ---
        # Decide value (URL takes precedence over default)
        value_to_set = final_value

        # If URL did not provide a value, use a copy of default
        if value_to_set is None:

            # Using deep copy to avoid shared references
            value_to_set = copy.deepcopy(default)
        
        # ---
        # Set it (triggers __setattr__, which updates session state and URL)
        setattr(cls, field, value_to_set)
        
        # Return the initialized value
        return value_to_set

    def _restore_url(cls):
        """
        Ensures that all URL query parameters defined in the class are present in the URL,
        restoring them from the session state if they are missing.

        This is useful when `restore_url_on_touch` is True (default). It triggers on any
        access (read or write) to ensure URL parameters are present, preventing the URL
        from getting out of sync if:
        1. A parameter is manually removed by the user from the browser URL.
        2. A parameter is cleared by another `url_selfish` state (which is also True by default).
        """
        
        # Prevent recursion
        if getattr(cls, "_is_restoring_url", False):
            return

        # Mark that we are restoring URL to avoid recursion
        cls._is_restoring_url = True
        
        try:
            prefix = cls._config.get("url_prefix", "")

            # Iterate over all defined state variables
            for field, metadata in cls._model_metadata.items():
                
                url_key = metadata.get("url_key")
                if not url_key:
                    continue
                    
                value = getattr(cls, field)
                value_map = metadata.get("value_map")

                # Handle None values
                if value is None:
                    if cls._config.get("ignore_none_url"):
                        continue
                    else:
                        value = ""

                # Restore the URL parameter only if it's missing
                final_url_key = f"{prefix}{url_key}"
                if final_url_key not in st.query_params:
                    url_value = convert_to_URL(field, value, value_map)
                    st.query_params[final_url_key] = url_value
        
        finally:
            # Unmark the restoring flag
            cls._is_restoring_url = False
    
    def _sync_url(cls, key: str, value: Any):
        """
        Synchronizes the URL query parameters with the given attribute value.
        """

        # Extracts the field metadata
        metadata = cls._model_metadata.get(key)

        url_key = metadata.get("url_key")
        value_map = metadata.get("value_map")

        # If URL syncing is not configured for this attribute, skip
        if not url_key:
            return
        
        # Apply prefix from Config
        prefix = cls._config.get("url_prefix", "")
        final_url_key = f"{prefix}{url_key}"

        # 1. Handle Selfishness
        if cls._config.get("url_selfish"):

            # Collect all allowed keys for this class (the attributes with url_key defined)
            allowed_keys = {
                f"{prefix}{m['url_key']}"
                for m in cls._model_metadata.values() if m.get("url_key")
            }
            
            # Add allowed keys from shared classes
            shared_classes = cls._config.get("share_url_with", [])
            for shared_item in shared_classes:
                shared_cls = None
                
                # Resolve shared classitem (could be class or string name)
                if isinstance(shared_item, type):
                    shared_cls = shared_item
                elif isinstance(shared_item, str):
                    shared_cls = _PAGE_STATE_REGISTRY.get(shared_item)

                # If found, add its allowed keys
                if shared_cls and hasattr(shared_cls, '_model_metadata'):

                    # Apply shared class prefix
                    shared_prefix = getattr(shared_cls, '_config', {}).get("url_prefix", "")
                    
                    # Collect shared class keys
                    shared_keys = {
                        f"{shared_prefix}{m['url_key']}"
                        for m in shared_cls._model_metadata.values() if m.get("url_key")
                    }

                    # Update allowed keys
                    allowed_keys.update(shared_keys)

            # ---
            # Keep only keys belonging to this class OR shared classes
            for k in list(st.query_params.keys()):

                if k not in allowed_keys:
                    del st.query_params[k]

        # ---
        # 2. Handle None values based on Config
        if value is None:

            # If configured to ignore None values in URL, remove the param
            if cls._config.get("ignore_none_url"):

                if final_url_key in st.query_params:
                    del st.query_params[final_url_key]

                return
            
            else:
                # If not ignoring None, we can represent it as an empty string
                value = ""
        
        # ---
        # 4. Convert the internal value to URL string
        url_value = convert_to_URL(key, value, value_map)

        # 5. Update the URL query parameters
        st.query_params[final_url_key] = url_value