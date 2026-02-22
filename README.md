# st-page-state

[![PyPI version](https://badge.fury.io/py/st-page-state.svg)](https://badge.fury.io/py/st-page-state)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/)

Declarative, typed, URL-aware state management for complex Streamlit apps.

**st-page-state** is an architectural pattern for Streamlit that replaces loose dictionary keys with strict, typed classes. It solves the friction of managing complex state, URL synchronization, and component communication in large-scale applications.

## The Magic: 20 Lines of Code Becomes 3

Stop writing boilerplate. Turn messy, hard-to-maintain state logic into clean, declarative code.

### Before: Native `st.session_state`

The old way is brittle, requires manual URL parsing, and lacks type safety.

```python
import streamlit as st

# 1. Initialize logic scattered across the script
if "status" not in st.session_state:

    # 2. Manual URL parsing
    url_val = st.query_params.get("status", "pending")
    st.session_state["status"] = url_val

# 3. No type safety
status = st.session_state["status"]

# 4. Manual URL updating on change
def update_status():
    st.query_params["status"] = st.session_state["status"]

st.selectbox("Status", ["pending", "active"], key="status", on_change=update_status)
```

### After: With `st-page-state`

Declarative, typed, and automatically synchronized with the URL.

```python
from st_page_state import PageState, StateVar

class FilterState(PageState):
    status: str = StateVar(default="pending", url_key="status")

st.selectbox("Status", ["pending", "active"], **FilterState.bind("status"))
```

## Killer Feature: Deep Linking & Sharable URLs

The #1 reason to use this library: **`st.session_state` dies on page refresh.**

When a user filters a app and shares the URL, their colleague sees a completely different view. **st-page-state** solves this by making the URL the source of truth.

*   **Shareable URLs:** Copy the URL, send it to a colleague, and they'll see the *exact same state*.
*   **Bookmarkable Views:** Users can bookmark a specific filtered view and come back to it days later.
*   **Deep Linking:** Programmatically generate links (e.g., in an email report) that open your app in a pre-configured state.

This is powered by **Automatic Bi-Directional Sync**:
1.  **On Load:** The app state is initialized from the URL.
2.  **On Change:** Any interaction with a bound widget instantly updates the URL.

## 📦 Installation

```bash
pip install st-page-state
```

*(Requires Python 3.8+ and Streamlit >= 1.30)*

## 📖 Core Patterns

### 1. Complex Data Types & URLs

Handling lists, sets, tuples, or dates in query parameters usually requires manual parsing logic. `st-page-state` handles serialization automatically using efficient Base64 encoding for lists to keep URLs clean and safe.

```python
class SearchState(PageState):
    # Serialized as Base64 JSON in URL
    tags: list[str] = StateVar(default=[], url_key="tags")
    
    # Sets work too (great for unique selections)
    categories: set[int] = StateVar(default={1, 2}, url_key="cats")

    # Automatically handles ISO format dates
    start_date: datetime.date = StateVar(default=datetime.date.today(), url_key="start")
```

*See `examples/06_list_handling.py` for a full demo.*

### 2. Value Mapping (Enums)

Decouple your internal logic (integers/IDs) from your public URLs (friendly strings).

```python
class TaskState(PageState):
    status: int = StateVar(
        default=0,
        url_key="status",
        value_map={
            0: "todo",        # URL shows ?status=todo
            1: "in_progress", # URL shows ?status=in_progress
            2: "done"         # URL shows ?status=done
        }
    )

# Your code works with clean integers
if TaskState.status == 1:
    st.info("Task is in progress")
```

### 3. Lifecycle Hooks

Stop cluttering your UI code with side effects. Define `on_init` and `on_change` logic directly where the state lives.

```python
class AppState(PageState):
    theme: str = StateVar(default="light")

    @classmethod
    def on_init(cls):
        """Runs once when the session starts."""
        print("State initialized.")

    @classmethod
    def on_change(cls, field, old_value, new_value):
        """Runs whenever a specific field changes."""
        if field == "theme":
            print(f"Theme changed from {old_value} to {new_value}")
            # Trigger external analytics, logging, or database updates here
```

### 4. Widget Binding

The `.bind()` method returns the exact dictionary (`key` and `on_change`) Streamlit widgets expect.

```python
st.text_input("Search", **SearchState.bind("query"))
```

#### Custom Initial Values
Sometimes you want a widget to start with a specific value without changing the global `StateVar` default. You can pass a `value` argument to `.bind()`:

```python
# The widget will start at 10 on the first run, even if the StateVar default is 0
st.number_input("Counter", **MyState.bind("count", value=10))
```

*See `examples/08_bind_initial_value.py` for a full demo.*

### 5. Advanced URL Control with `Config`

For multi-page or complex apps, you might need finer control over the URL query string. The inner `Config` class provides this.

```python
class DashboardState(PageState):
    class Config:
        # 1. Add a prefix to all URL keys from this class
        url_prefix = "dash_"

        # 2. If True (default), remove any URL params not managed by this class
        url_selfish = True

        # 3. If True (default), restore any missing URL params from session state on every change
        restore_url_on_touch = True

        # 4. List of other PageState classes (by name or Class obj) to share the URL with
        share_url_with = ["OtherState"] # Or share_url_with = [OtherState]
    
    tab: str = StateVar(default="overview", url_key="tab") # -> ?dash_tab=overview
    show_details: bool = StateVar(default=False, url_key="details") # -> ?dash_details=true
```

*   `url_prefix`: Prevents key collisions between different `PageState` models.
*   `url_selfish`: **(Default: True)** When any variable in a selfish state changes, it clears all other query parameters from the URL. This ensures a clean URL that only reflects the active component.
*   `restore_url_on_touch`: **(Default: True)** Guarantees URL completeness. It ensures that whenever you access (read or write) a state variable, its corresponding URL parameter is present. This restores parameters if they were missing due to:
    1.  Manual removal by the user from the browser URL.
    2.  Clearing by another `url_selfish` state.
*   `share_url_with`: **(List[str] | List[Type[PageState]])** A list of other `PageState` class names (strings) or class objects that this state should share the URL with. Even if `url_selfish` is True, parameters belonging to the specified classes will be preserved in the URL instead of being cleared.

*See `examples/07_config_class.py` for a full demo.*

## Advanced Tooling

### Programmatic URL Focus

Sometimes you need to claim URL focus without user interaction. The `.focus()` method programmatically triggers the `url_selfish` and `restore_url_on_touch` logic.

```python
# Clears any non-DashboardState params and ensures all its own params are in the URL
DashboardState.focus()
```

For complex apps, visibility into your state is critical.

```python
# Get a pure dictionary of current values (great for API payloads)
payload = UserState.dump() 

# Reset specific fields or the entire state to defaults
UserState.reset()
```

## 🤝 Contributing

We welcome contributions from the community. If you are solving complex state problems in Streamlit, we want to hear from you.

1.  Fork the repository
2.  Create your feature branch
3.  Install dev dependencies (`pip install -e .[dev]`)
4.  Run tests (`pytest`)
5.  Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.
