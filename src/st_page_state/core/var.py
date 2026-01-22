from typing import Any, Dict, Optional

class StateVar:
    """
    Helper class for defining session state variables declaratively.

    This class acts as a descriptor/placeholder that `PageStateMeta` uses to configure
    session state handling and URL synchronization for a specific attribute.

    When accessed, the `PageStateMeta` will handle getting and setting the value
    in the session state accordingly.

    Example:
        class MyPageState(PageStateBase):
        
            #### Define a state variable synchronized with '?my_var_qp=...'
            my_var: str = StateVar(
                default="default_value",
                url_key="my_var_qp",
                value_map={"url_val": "Internal Value"}
            )
    """

    def __init__(
        self,
        default: Any,
        url_key: Optional[str] = None,
        value_map: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a StateVar instance.

        :param default: The default value for the state variable.
        :type default: Any
        :param url_key: (Optional) The URL query parameter key to sync with.
        :type url_key: str, optional
        :param value_map: (Optional) A dictionary mapping URL string values to internal values.
                          e.g. {'url_val': 'Internal Value'}
        :type value_map: Dict[str, Any], optional
        """

        # Store parameters
        self.default = default
        self.url_key = url_key
        self.value_map = value_map