import sys
import datetime
import pytest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Fake redis module — registered before any import touches it
# ---------------------------------------------------------------------------

class _FakeRedis:
    """Dict-backed stand-in for ``redis.StrictRedis``."""
    def __init__(self, **kw):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value):
        self._store[key] = value

    def setex(self, key, ttl, value):
        self._store[key] = value

    def delete(self, key):
        self._store.pop(key, None)

    def ping(self):
        return True

    def scan(self, cursor, match=None, count=100):
        """Simulate SCAN with glob-style pattern matching."""
        import fnmatch
        matched = [k for k in self._store if fnmatch.fnmatch(k, match or "*")]
        return (0, matched)

_fake_redis_mod = MagicMock()
_fake_redis_mod.StrictRedis = _FakeRedis
sys.modules.setdefault("redis", _fake_redis_mod)

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

from st_page_state.utils.converters import serialize_state, deserialize_state
from st_page_state.backends.redis_backend import RedisBackend


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _wait_save(backend: RedisBackend, timeout: float = 2.0):
    """Block until the backend's async save thread finishes."""
    t = backend._last_save_thread
    if t is not None:
        t.join(timeout)


@pytest.fixture()
def backend():
    return RedisBackend(default_ttl=300)


# ═══════════════════════════════════════════════════════════════════════════
# Serialization
# ═══════════════════════════════════════════════════════════════════════════

class TestStateSerialization:

    @pytest.mark.parametrize("data", [
        {"count": 42, "name": "hello"},
        {"flag": True, "ratio": 3.14},
        {},
    ])
    def test_primitive_roundtrip(self, data):
        assert deserialize_state(serialize_state(data)) == data

    def test_datetime_roundtrip(self):
        data = {"dt": datetime.datetime(2025, 6, 15, 12, 0, 0)}
        assert deserialize_state(serialize_state(data)) == data

    def test_date_roundtrip(self):
        data = {"d": datetime.date(2025, 1, 1)}
        assert deserialize_state(serialize_state(data)) == data

    def test_time_roundtrip(self):
        data = {"t": datetime.time(9, 30)}
        assert deserialize_state(serialize_state(data)) == data

    def test_set_roundtrip(self):
        data = {"s": {1, 2, 3}}
        assert deserialize_state(serialize_state(data)) == data

    def test_tuple_roundtrip(self):
        data = {"tp": (10, 20)}
        assert deserialize_state(serialize_state(data)) == data

    def test_bytes_roundtrip(self):
        data = {"b": b"\x00\xff\xfe"}
        assert deserialize_state(serialize_state(data)) == data

    def test_nested_datetime_in_tuple(self):
        data = {"pair": (datetime.datetime(2025, 1, 1), datetime.date(2025, 6, 15))}
        assert deserialize_state(serialize_state(data)) == data

    def test_nested_set_in_dict(self):
        data = {"items": {"tags": {1, 2, 3}}}
        assert deserialize_state(serialize_state(data)) == data

    def test_non_serializable_replaced_with_none(self):
        """Non-JSON-serializable values are dropped to None instead of crashing."""

        data = {"good": 42, "bad": lambda x: x, "also_bad": object()}
        result = deserialize_state(serialize_state(data))
        
        assert result["good"] == 42
        assert result["bad"] is None
        assert result["also_bad"] is None


# ═══════════════════════════════════════════════════════════════════════════
# RedisBackend CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestRedisBackendCRUD:

    def test_save_and_load(self, backend):
        backend.save("MyState", "sess-1", {"count": 42}, ttl=None)
        assert backend.load("MyState", "sess-1") == {"count": 42}

    def test_load_missing_returns_none(self, backend):
        assert backend.load("Missing", "sess-x") is None

    def test_save_with_ttl_uses_setex(self, backend):
        backend._client.setex = MagicMock()
        backend.save("S", "sess", {"a": 1}, ttl=60)
        backend._client.setex.assert_called_once()
        assert backend._client.setex.call_args[0][1] == 60

    def test_save_without_ttl_uses_set(self, backend):
        backend._client.set = MagicMock()
        backend.save("S", "sess", {"a": 1}, ttl=None)
        backend._client.set.assert_called_once()

    def test_delete(self, backend):
        backend.save("S", "sess", {"x": 1}, ttl=None)
        backend.delete("S", "sess")
        assert backend.load("S", "sess") is None

    def test_ping(self, backend):
        assert backend.ping() is True

    def test_key_format(self, backend):
        assert backend._key("Cls", "abc") == "st_page_state:abc:Cls"

    def test_load_survives_error(self, backend):
        backend._client.get = MagicMock(side_effect=Exception("boom"))
        assert backend.load("S", "sess") is None

    def test_save_survives_error(self, backend):
        backend._client.set = MagicMock(side_effect=Exception("boom"))
        backend.save("S", "sess", {"a": 1}, ttl=None)


# ═══════════════════════════════════════════════════════════════════════════
# TTL resolution
# ═══════════════════════════════════════════════════════════════════════════

class TestResolveTTL:

    def test_class_ttl_wins(self, backend):
        class State:
            class Config:
                ttl = 120
        assert backend.resolve_ttl(State) == 120

    def test_falls_back_to_global(self, backend):
        class State:
            class Config:
                url_selfish = True
        assert backend.resolve_ttl(State) == 300

    def test_no_config_falls_back_to_global(self, backend):
        class State:
            pass
        assert backend.resolve_ttl(State) == 300

    def test_class_ttl_none_means_no_expiry(self):
        b = RedisBackend(default_ttl=3600)
        class State:
            class Config:
                ttl = None
        assert b.resolve_ttl(State) is None


# ═══════════════════════════════════════════════════════════════════════════
# Constructor
# ═══════════════════════════════════════════════════════════════════════════

class TestConstructor:

    def test_stores_config(self):
        b = RedisBackend(host="myhost", default_ttl=120)
        assert b.host == "myhost"
        assert b.default_ttl == 120

    def test_default_values(self):
        b = RedisBackend()
        assert b.host == "localhost"
        assert b.port == 6379
        assert b.default_ttl is None
        assert b.key_prefix == "st_page_state"

    def test_session_id_string(self):
        b = RedisBackend(session_id="juan")
        assert b._session_id() == "juan"

    def test_session_id_callable(self):
        b = RedisBackend(session_id=lambda: "user-42")
        assert b._session_id() == "user-42"

    def test_session_id_none_falls_back_to_default(self):
        b = RedisBackend(session_id=None)
        # Outside a Streamlit runtime the fallback is "default"
        assert b._session_id() == "default"

    def test_client_reused_across_instances(self):
        """The same instance is returned from session_state on subsequent calls."""
        b1 = RedisBackend()
        b2 = RedisBackend()
        assert b1 is b2


# ═══════════════════════════════════════════════════════════════════════════
# session() context manager
# ═══════════════════════════════════════════════════════════════════════════

class TestSession:

    def test_load_and_save_roundtrip(self):
        import streamlit as st
        from st_page_state import PageState, StateVar
        from st_page_state.core.meta import SESSION_STATE_KEY

        b = RedisBackend(default_ttl=600)
        b.save("RoundTripState", "default", {"count": 99}, ttl=None)

        class RoundTripState(PageState):
            count: int = StateVar(default=0)

        with b.session():
            ns = st.session_state.get(SESSION_STATE_KEY, {}).get("RoundTripState", {})
            assert ns.get("count") == 99
            RoundTripState.count = 200

        _wait_save(b)
        saved = b.load("RoundTripState", "default")
        assert saved["count"] == 200

    def test_per_class_ttl(self):
        from st_page_state import PageState, StateVar

        spy_setex = MagicMock(side_effect=_FakeRedis().setex)
        b = RedisBackend(default_ttl=3600)
        b._client.setex = spy_setex

        class ShortLivedState(PageState):
            val: str = StateVar(default="x")
            class Config:
                ttl = 30

        with b.session():
            ShortLivedState.val = "hello"

        _wait_save(b)
        assert spy_setex.called
        assert spy_setex.call_args[0][1] == 30

    def test_skip_load_when_session_is_warm(self):
        """Redis load is skipped when session_state already has data."""
        import streamlit as st
        from st_page_state import PageState, StateVar
        from st_page_state.core.meta import SESSION_STATE_KEY

        b = RedisBackend(default_ttl=600)

        class WarmState(PageState):
            count: int = StateVar(default=0)

        b.save("WarmState", "default", {"count": 50}, ttl=None)

        # Simulate a warm session
        st.session_state.setdefault(SESSION_STATE_KEY, {})
        st.session_state[SESSION_STATE_KEY]["WarmState"] = {"count": 100}

        with b.session():
            ns = st.session_state[SESSION_STATE_KEY]["WarmState"]
            assert ns["count"] == 100

    def test_custom_session_id_string(self):
        """A fixed session_id string routes all data under that identity."""
        import streamlit as st
        from st_page_state import PageState, StateVar
        from st_page_state.core.meta import SESSION_STATE_KEY

        b = RedisBackend(default_ttl=600, session_id="juan")
        b.save("IdState", "juan", {"val": 7}, ttl=None)

        class IdState(PageState):
            val: int = StateVar(default=0)

        with b.session():
            ns = st.session_state.get(SESSION_STATE_KEY, {}).get("IdState", {})
            assert ns.get("val") == 7
            IdState.val = 42

        _wait_save(b)
        assert b.load("IdState", "juan")["val"] == 42

    def test_custom_session_id_callable(self):
        """A callable session_id is invoked each time."""
        import streamlit as st
        from st_page_state import PageState, StateVar
        from st_page_state.core.meta import SESSION_STATE_KEY

        current_user = "alice"
        b = RedisBackend(default_ttl=600, session_id=lambda: current_user)
        b.save("CallState", "alice", {"n": 5}, ttl=None)

        class CallState(PageState):
            n: int = StateVar(default=0)

        with b.session():
            ns = st.session_state.get(SESSION_STATE_KEY, {}).get("CallState", {})
            assert ns.get("n") == 5

        _wait_save(b)
        assert b.load("CallState", "alice")["n"] == 5


# ═══════════════════════════════════════════════════════════════════════════
# Identity transition
# ═══════════════════════════════════════════════════════════════════════════

class TestIdentityTransition:

    def test_identity_change_clears_and_reloads(self):
        """When session_id changes, old state is wiped and new user data loads."""
        import streamlit as st
        from st_page_state import PageState, StateVar
        from st_page_state.core.meta import SESSION_STATE_KEY

        identity = "anonymous"
        b = RedisBackend(default_ttl=600, session_id=lambda: identity)

        # Pre-populate Redis with data for both identities
        b.save("TransState", "anonymous", {"val": 0}, ttl=None)
        b.save("TransState", "juan", {"val": 99}, ttl=None)

        class TransState(PageState):
            val: int = StateVar(default=0)

        # First run: anonymous
        with b.session():
            ns = st.session_state.get(SESSION_STATE_KEY, {}).get("TransState", {})
            assert ns.get("val") == 0  # loaded from anonymous key

        _wait_save(b)

        # User "logs in"
        identity = "juan"

        # Second run: session_id now returns "juan"
        with b.session():
            ns = st.session_state.get(SESSION_STATE_KEY, {}).get("TransState", {})
            assert ns.get("val") == 99  # old state wiped; loaded from juan key

    def test_same_identity_keeps_warm_session(self):
        """Repeated runs with the same identity don't re-load (session is warm)."""
        import streamlit as st
        from st_page_state import PageState, StateVar
        from st_page_state.core.meta import SESSION_STATE_KEY

        b = RedisBackend(default_ttl=600, session_id="bob")
        b.save("WarmCheck", "bob", {"x": 10}, ttl=None)

        class WarmCheck(PageState):
            x: int = StateVar(default=0)

        # First run — loads from Redis
        with b.session():
            ns = st.session_state[SESSION_STATE_KEY]["WarmCheck"]
            assert ns["x"] == 10
            # Mutate in session
            WarmCheck.x = 55

        _wait_save(b)

        # Second run — same identity, session is warm → keeps 55
        with b.session():
            ns = st.session_state[SESSION_STATE_KEY]["WarmCheck"]
            assert ns["x"] == 55


# ═══════════════════════════════════════════════════════════════════════════
# URL priority over Redis
# ═══════════════════════════════════════════════════════════════════════════

class TestURLPriorityOverRedis:

    def test_url_param_takes_precedence_over_redis(self):
        """Fields whose url_key is in query_params are skipped during Redis LOAD."""
        import streamlit as st
        from st_page_state import PageState, StateVar
        from st_page_state.core.meta import SESSION_STATE_KEY

        b = RedisBackend(default_ttl=600, session_id="url-test")
        b.save("URLState", "url-test", {"page": "home", "count": 42}, ttl=None)

        class URLState(PageState):
            page: str = StateVar(default="index", url_key="p")
            count: int = StateVar(default=0)

        # Simulate a URL with ?p=settings
        st.query_params["p"] = "settings"

        with b.session():
            ns = st.session_state.get(SESSION_STATE_KEY, {}).get("URLState", {})
            # "page" was NOT loaded from Redis because ?p= is in query_params
            assert "page" not in ns
            # "count" WAS loaded from Redis (no url_key conflict)
            assert ns.get("count") == 42

    def test_no_url_overlap_loads_everything(self):
        """When no URL params overlap, all fields load from Redis normally."""
        import streamlit as st
        from st_page_state import PageState, StateVar
        from st_page_state.core.meta import SESSION_STATE_KEY

        b = RedisBackend(default_ttl=600, session_id="full-load")
        b.save("FullState", "full-load", {"a": 1, "b": 2}, ttl=None)

        class FullState(PageState):
            a: int = StateVar(default=0, url_key="qa")
            b: int = StateVar(default=0, url_key="qb")

        # No query params set → everything loads from Redis
        with b.session():
            ns = st.session_state.get(SESSION_STATE_KEY, {}).get("FullState", {})
            assert ns.get("a") == 1
            assert ns.get("b") == 2
