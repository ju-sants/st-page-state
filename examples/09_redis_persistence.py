"""
Redis Persistence Example

Demonstrates how to persist PageState to Redis so that
state survives server restarts and can be shared across deployments.

Prerequisites:
    pip install st-page-state[redis]
    # A running Redis server (default: localhost:6379)

Key concepts:
    1. RedisBackend(...) creates the connection once.
    2. redis.session() loads state on entry and saves it on exit.
    3. Per-class Config.ttl overrides the global default_ttl.
    4. session_id lets you control the identity used for Redis keys.
       - None  → Streamlit's ephemeral session ID (default).
       - str   → a fixed identity, e.g. "juan".
       - callable → resolved on every run, e.g.
         lambda: st.session_state.get("user_email", "anonymous")
"""

import streamlit as st
from st_page_state import PageState, StateVar, RedisBackend

st.set_page_config(page_title="Redis Persistence Example")

# ---------------------------------------------------------------------------
# 1. Create the Redis backend (once, before any state access)
# ---------------------------------------------------------------------------
r_backend = RedisBackend(
    host="localhost",
    port=6379,

    default_ttl=3600,       # all keys expire after 1 hour by default
    key_prefix="example",   # Redis keys: example:<session_id>:<ClassName>

    # session_id controls whose state is loaded / saved.
    # Use a callable so the identity is resolved on each Streamlit rerun:
    session_id=lambda: st.session_state.get("user_email", "anonymous"),
    
    # Or pass a plain string for a fixed identity:
    # session_id="juan",
)

# ---------------------------------------------------------------------------
# 2. Define state classes
# ---------------------------------------------------------------------------

class CounterState(PageState):
    """Long-lived counter — uses the global default_ttl (1 hour)."""
    count: int = StateVar(default=0, url_key="count")


class DraftState(PageState):
    """Short-lived draft — expires after 2 minutes."""
    text: str = StateVar(default="")

    class Config:
        ttl = 120  # overrides default_ttl for this class


# ---------------------------------------------------------------------------
# 3. Wrap your page in r_backend.session()
# ---------------------------------------------------------------------------
with r_backend.session():

    st.title("Redis Persistence")
    st.caption("State is saved to Redis on every run and restored on the next.")

    # --- Counter (persistent) ---
    st.subheader("Persistent Counter")
    st.metric("Count", CounterState.count)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("＋", use_container_width=True):
            CounterState.count += 1
            st.rerun()
    with col2:
        if st.button("－", use_container_width=True):
            CounterState.count -= 1
            st.rerun()
    with col3:
        if st.button("Reset", type="primary", use_container_width=True):
            CounterState.reset("count")
            st.rerun()

    st.divider()

    # --- Draft (ephemeral) ---
    st.subheader("Ephemeral Draft (TTL = 120 s)")
    st.text_area("Write something…", **DraftState.bind("text"))
    st.info(
        "This draft is stored in Redis with a 2-minute TTL. "
        "Restart the server within that window and your text will still be here."
    )

    st.divider()

    # --- Inspect ---
    with st.expander("Debug: current state"):
        st.json({"CounterState": CounterState.dump(), "DraftState": DraftState.dump()})
