import streamlit as st
import logging
import threading
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ..core.meta import _PAGE_STATE_REGISTRY, SESSION_STATE_KEY
from ..utils.converters import deserialize_state, serialize_state

logger = logging.getLogger(__name__)


class RedisBackend:
    """Single entry-point for Redis-backed state persistence.

    Holds the connection configuration, the ``redis.StrictRedis`` client,
    and exposes :meth:`session` as the context-manager wrapper around
    Streamlit's script-run lifecycle.

    Parameters match ``redis.StrictRedis`` plus a few extras:

    *default_ttl* — seconds before a key expires (overridable per-class
    via ``Config.ttl``).  ``None`` means no expiry.

    *key_prefix* — namespaces every Redis key as
    ``<prefix>:<session_id>:<ClassName>``.

    *session_id* — controls how the current user is identified.

    * ``None`` (default) — uses the Streamlit session ID (ephemeral;
      each browser tab gets its own ID).
    * ``str`` — a fixed identity string, e.g. ``"juan"``.
    * ``Callable[[], str]`` — called on every script run so you can
      resolve the identity lazily, e.g.
      ``lambda: st.session_state.get("user_email", "anonymous")``.

    **Identity transition** — when using a callable that changes its
    return value (e.g. ``"anonymous"`` → ``"juan@mail.com"`` after login),
    the in-memory session state is automatically cleared so the new
    user's data loads fresh from Redis.  No stale anonymous data leaks
    into the real user's namespace.

    **URL priority** — fields whose ``url_key`` appears in the current
    ``query_params`` are *skipped* during Redis LOAD, so shared URLs
    (``?page=settings&tab=2``) always win over whatever was last saved.

    **Rerun-safe** — the instance is cached in ``st.session_state`` so
    that ``RedisBackend(...)`` at module level reuses the same object
    (and TCP connection) across Streamlit reruns.
    """

    _INSTANCE_KEY = "_st_page_state_redis_backend"

    def __new__(cls, *args: Any, **kwargs: Any):
        cached = st.session_state.get(cls._INSTANCE_KEY)
        if cached is not None:

            # Refresh per-rerun settings
            cached.default_ttl = kwargs.get("default_ttl", args[4] if len(args) > 4 else None)
            cached._session_id_resolver = kwargs.get("session_id", args[8] if len(args) > 8 else None)
            return cached
        
        return super().__new__(cls)

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: Optional[int] = None,
        key_prefix: str = "st_page_state",
        ssl: bool = False,
        socket_timeout: Optional[float] = None,
        session_id: Optional[Union[str, Callable[[], str]]] = None,
        **kwargs: Any,
    ) -> None:
        
        # Already initialised — __new__ returned the cached instance
        if st.session_state.get(self._INSTANCE_KEY) is self:
            return

        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.ssl = ssl
        self.socket_timeout = socket_timeout
        self.extra_kwargs = kwargs
        self._session_id_resolver = session_id
        self._last_save_thread: Optional[threading.Thread] = None

        self._client = self._connect()
        st.session_state[self._INSTANCE_KEY] = self

        logger.debug(f"Redis configured – {host}:{port} db={db}")

    # -- connection ----------------------------------------------------------

    def _connect(self):
        try:
            import redis as _redis

        except ImportError as exc:
            raise ImportError(
                "The 'redis' package is required for Redis state persistence.\n"
                "Install it with:  pip install st-page-state[redis]"
            ) from exc

        return _redis.StrictRedis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            ssl=self.ssl,
            socket_timeout=self.socket_timeout,
            decode_responses=True,
            **self.extra_kwargs,
        )

    # -- key / TTL -----------------------------------------------------------

    def _key(self, class_name: str, session_id: str) -> str:
        return f"{self.key_prefix}:{session_id}:{class_name}"

    def resolve_ttl(self, state_cls) -> Optional[int]:
        """``Config.ttl`` on the class → ``default_ttl`` → ``None``."""

        cfg = getattr(state_cls, "Config", None)
        if cfg is not None and hasattr(cfg, "ttl"):
            return getattr(cfg, "ttl")
        
        return self.default_ttl

    # -- CRUD ----------------------------------------------------------------

    def load(self, class_name: str, session_id: str) -> Optional[Dict[str, Any]]:
        key = self._key(class_name, session_id)

        try:
            raw = self._client.get(key)
            return deserialize_state(raw) if raw is not None else None
        
        except Exception as exc:
            logger.warning(f"Redis load failed [{key}]: {exc}")
            return None

    def load_all(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        """Load every class namespace stored for *session_id*.

        Uses ``SCAN`` with the key pattern so no registry lookup is needed.
        Returns ``{class_name: {field: value, ...}, ...}``.
        """
        pattern = f"{self.key_prefix}:{session_id}:*"
        prefix_len = len(f"{self.key_prefix}:{session_id}:")
        result: Dict[str, Dict[str, Any]] = {}

        try:
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor, match=pattern, count=100)
                for key in keys:
                    class_name = key[prefix_len:]
                    data = self.load(class_name, session_id)
                    if data:
                        result[class_name] = data
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning(f"Redis scan failed [{pattern}]: {exc}")

        return result

    def save(self, class_name: str, session_id: str, data: Dict[str, Any], ttl: Optional[int]) -> None:
        key = self._key(class_name, session_id)
        try:

            payload = serialize_state(data)
            if ttl:
                self._client.setex(key, ttl, payload)

            else:
                self._client.set(key, payload)

        except Exception as exc:
            logger.warning(f"Redis save failed [{key}]: {exc}")

    def delete(self, class_name: str, session_id: str) -> None:
        key = self._key(class_name, session_id)
        try:

            self._client.delete(key)

        except Exception as exc:
            logger.warning(f"Redis delete failed [{key}]: {exc}")

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        
        except Exception:
            return False

    # -- session context manager ---------------------------------------------

    @contextmanager
    def session(self):
        """Load all stored state from Redis on entry, save it back (async) on exit.

        Each PageState class is stored as an independent key.
        TTL is resolved per class (``Config.ttl`` → ``default_ttl`` → no expiry).

        **Identity transition** — if the resolved ``session_id`` changes between
        reruns (e.g. anonymous → logged-in user), the in-memory state is wiped
        so the new user's data loads cleanly from Redis.

        **URL priority** — fields whose ``url_key`` appears in the current
        ``query_params`` are *skipped* during LOAD so Streamlit's URL→state
        initialisation takes precedence.
        """
        sid = self._session_id()

        # ---
        # IDENTITY TRANSITION — detect when the session_id changes and wipe
        # stale in-memory state so the new user's data loads fresh.
        _SID_MARKER = "_st_page_state_sid"
        prev_sid = st.session_state.get(_SID_MARKER)

        if prev_sid is not None and prev_sid != sid:

            # Identity changed — clear all PageState namespaces
            st.session_state.pop(SESSION_STATE_KEY, None)
            logger.debug(f"Identity changed ({prev_sid!r} → {sid!r}) — session state cleared")

        st.session_state[_SID_MARKER] = sid

        # ---
        # LOAD — restore from Redis, but respect two rules:
        #   1. Skip classes whose session_state namespace is already warm.
        #   2. Skip individual fields that have a URL query-param present
        #      (let _initialize_attribute's URL-first logic handle them).
        existing = st.session_state.get(SESSION_STATE_KEY, {})

        # Build a set of URL keys currently in the address bar
        current_qp = set(st.query_params.keys()) if hasattr(st, "query_params") else set()

        for class_name, fields in self.load_all(sid).items():
            if class_name in existing and existing[class_name]:
                continue  # session already warm for this class

            # Determine which URL keys belong to this class
            cls_obj = _PAGE_STATE_REGISTRY.get(class_name)
            url_fields = set()
            if cls_obj is not None:

                prefix = getattr(cls_obj, "_config", {}).get("url_prefix", "")
                for meta in getattr(cls_obj, "_model_metadata", {}).values():

                    uk = meta.get("url_key")
                    if uk:

                        url_fields.add(f"{prefix}{uk}")

            # Filter out fields whose URL key is in query_params
            if url_fields & current_qp:

                # Only keep fields that do NOT have a URL override
                field_meta = getattr(cls_obj, "_model_metadata", {}) if cls_obj else {}
                filtered: dict = {}

                for fname, fval in fields.items():

                    meta = field_meta.get(fname, {})
                    uk = meta.get("url_key")
                    full_uk = f"{prefix}{uk}" if uk else None

                    if full_uk and full_uk in current_qp:

                        logger.debug(f"Skipping '{class_name}.{fname}' — URL param '{full_uk}' takes precedence")
                        continue

                    filtered[fname] = fval
                fields = filtered

            if not fields:
                continue

            st.session_state.setdefault(SESSION_STATE_KEY, {}).setdefault(class_name, {})
            st.session_state[SESSION_STATE_KEY][class_name].update(fields)

            logger.debug(f"Restored {len(fields)} field(s) for '{class_name}' from Redis (session={sid})")

        try:
            yield

        finally:
            self._save(sid)

    # -- internals -----------------------------------------------------------

    def _session_id(self) -> str:
        """Resolve the current session identity.

        Priority: explicit *session_id* passed to the constructor
        (string or callable) → Streamlit's runtime session ID → ``"default"``.
        """
        resolver = self._session_id_resolver

        if isinstance(resolver, str):
            return resolver

        if callable(resolver):
            return resolver()

        # Fallback: Streamlit runtime session ID
        try:

            from streamlit.runtime.scriptrunner import get_script_run_ctx
            ctx = get_script_run_ctx()

            if ctx is not None:
                return ctx.session_id
            
        except Exception:
            pass
        return "default"

    def _save(self, session_id: str) -> None:
        """Snapshot every class namespace and persist in a daemon thread."""
        all_ns = st.session_state.get(SESSION_STATE_KEY, {})
        payloads: List[Tuple[str, Dict[str, Any], Optional[int]]] = []

        for class_name, class_ns in all_ns.items():
            if not class_ns:
                continue

            # Resolve TTL from the registry if the class is known, else use global default
            state_cls = _PAGE_STATE_REGISTRY.get(class_name)
            ttl = self.resolve_ttl(state_cls) if state_cls else self.default_ttl

            payloads.append((class_name, dict(class_ns), ttl))

        if payloads:

            t = threading.Thread(target=self._save_worker, args=(session_id, payloads), daemon=True)
            t.start()
            self._last_save_thread = t

    def _save_worker(self, session_id: str, payloads: "List[Tuple[str, Dict[str, Any], Optional[int]]]") -> None:
        for class_name, data, ttl in payloads:
            self.save(class_name, session_id, data, ttl)

            logger.debug(f"Saved {len(data)} field(s) for '{class_name}' (session={session_id}, ttl={ttl})")
