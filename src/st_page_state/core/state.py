import streamlit as st

from .meta import PageStateMeta, SESSION_STATE_KEY

class PageState(metaclass=PageStateMeta):
    """
    Base class for defining page state classes.

    Inheriting from this class enables the `PageStateMeta` metaclass capabilities,
    allowing declarative definition of session state variables and query params sync using `StateVar`
    or the `_model_metadata` dictionary.
    """

    @classmethod
    def schema(cls):
        """Returns the metadata definition of the state."""

        return cls._model_metadata

    @classmethod
    def dump(cls):
        """Returns a dict copy of the current session state values."""

        # If there is session state for this class, return a copy of it
        if SESSION_STATE_KEY in st.session_state:
            return dict(st.session_state[SESSION_STATE_KEY].get(cls.__name__, {}))
        
        # Otherwise, return an empty dict
        return {}

    @classmethod
    def reset(cls, field: str = None):
        """Resets all fields to their default values."""

        for state_field, metadata in cls._model_metadata.items():
            
            # Logic to reset only a specific field or all of them
            if not field or field == state_field:

                # Gets the default value
                default = metadata['default']

                # Sets it using setattr (triggers __setattr__ in the metaclass, which updates session state and URL)
                setattr(cls, state_field, default)

    @classmethod
    def bind(cls, field: str):
        """
        Binds a Streamlit widget to a state variable.

        This method prepares the session state to synchronize a widget with a state variable.
        It sets the initial value, generates a unique key, and provides a callback
        to update the state when the widget changes.

        :param field: The name of the state variable to bind.
        :return: A dictionary with 'key' and 'on_change' to be unpacked into the widget.
        """

        # Gets the metadata for the field - raises an error if not found
        metadata = cls._model_metadata.get(field)
        if not metadata:
            raise ValueError(f"Field '{field}' is not defined in the PageState.")

        # Creates a unique key for the widget
        widget_key = f"{cls.__name__}_{field}_widget"

        # Sets the initial value for the widget in session state - this will be used by the widget when rendered
        initial_value = getattr(cls, field)
        st.session_state[widget_key] = initial_value

        # Defines the callback function to update the state variable
        def callback():

            # Gets the new value from session state
            new_value = st.session_state.get(widget_key)

            # Updates the state variable using setattr (triggers __setattr__ in the metaclass, which updates session state and URL)
            setattr(cls, field, new_value)

        # Returns the binding information
        return {
            'key': widget_key,
            'on_change': callback,
        }