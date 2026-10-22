# services/key_pool_router.py
"""Key‑Pool router & error‑rate telemetry.

Provides:
* `load_keys()` – reads Gemini and auxiliary provider keys from the environment
  (GEMINI_KEY_POOL, GEMINI_API_KEY, GEMINI_ISSUE_KEY, …) and from ``.gemini_keys`` files.
* `KeyPoolRouter` – a thread‑safe singleton that tracks per‑key request statistics
  over a rolling 5‑minute window and implements the 25 % error‑rate circuit breaker.
* `track_error_rate` – decorator used around any LLM call. It automatically selects
  an ``ACTIVE`` key, records success/failure, and retries on the next healthy key
  (up to 5 attempts). Explicit ``429`` or ``5xx`` responses trigger an immediate
  ``COOLDOWN`` for 60 seconds.
"""

from __future__ import annotations

import os
import time
import threading
import collections
from typing import Callable, Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Helper – load raw API keys from env / .gemini_keys files
# ---------------------------------------------------------------------------


def _load_raw_keys() -> List[str]:
    """Collect all provider keys.

    The function mirrors the logic from ``scripts/autonomous_loop.py`` but is
    isolated so the rest of the code base can import it without side‑effects.
    """
    keys: List[str] = []
    # 1. Explicit pool env var – comma separated list
    pool_env = os.getenv("GEMINI_KEY_POOL", "")
    keys.extend([k.strip() for k in pool_env.split(",") if k.strip()])

    # 2. Individual GEMINI_* vars (primary, issue, reviewer, solver)
    for var in ("GEMINI_API_KEY", "GEMINI_ISSUE_KEY", "GEMINI_REVIEWER_KEY", "GEMINI_SOLVER_KEY"):
        val = os.getenv(var, "").strip()
        if val and val not in keys:
            keys.append(val)

    # 3. .gemini_keys files in a few locations (repo root, script dir, home)
    candidate_dirs = [
        os.getcwd(),
        os.path.dirname(__file__),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        os.path.expanduser("~"),
    ]
    for d in candidate_dirs:
        f = os.path.join(d, ".gemini_keys")
        if os.path.isfile(f):
            try:
                for line in open(f, encoding="utf-8"):
                    k = line.strip()
                    if k and not k.startswith("#") and k not in keys:
                        keys.append(k)
            except Exception:
                pass
    return keys


# ---------------------------------------------------------------------------
# Core router class
# ---------------------------------------------------------------------------


class KeyMetrics:
    """Thread‑safe rolling error‑rate metrics for a single API key.

    Internally stores a ``deque`` of ``(timestamp, is_error)`` tuples.  The
    ``prune`` method discards entries older than 300 seconds.
    """

    def __init__(self) -> None:
        self._events: collections.deque[Tuple[float, bool]] = collections.deque()
        self._lock = threading.Lock()
        self._cooldown_until: float = 0.0

    def record(self, success: bool) -> None:
        now = time.time()
        with self._lock:
            self._events.append((now, not success))
            self.prune()

    def prune(self) -> None:
        cutoff = time.time() - 300  # 5 minutes
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def error_rate(self) -> float:
        with self._lock:
            self.prune()
            total = len(self._events)
            if total == 0:
                return 0.0
            errors = sum(1 for _, is_err in self._events if is_err)
            return errors / total

    def should_cooldown(self) -> bool:
        """Return ``True`` when the key must enter cooldown.

        - Immediate cooldown if a recent ``429``/``5xx`` was recorded (handled by the
          caller via ``record_failure`` with ``force=True``).
        - Otherwise, trigger when we have at least 4 samples **and** error_rate >=
          0.25.
        """
        with self._lock:
            self.prune()
            total = len(self._events)
            if total < 4:
                return False
            return self.error_rate() >= 0.25

    def set_cooldown(self, seconds: int = 60) -> None:
        self._cooldown_until = time.time() + seconds

    def is_cooldown(self) -> bool:
        return time.time() < self._cooldown_until


class KeyPoolRouter:
    """Singleton that routes LLM calls through a healthy key pool.

    Usage example:
    ```python
    router = KeyPoolRouter.get_instance()
    @router.track_error_rate
    def call_gemini(prompt: str, *, key: str = "") -> str:
        ...  # actual provider SDK call
    ```
    """

    _instance: "KeyPoolRouter | None" = None
    _inst_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "KeyPoolRouter":
        with cls._inst_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self) -> None:
        # Load raw keys once at startup
        self._raw_keys: List[str] = _load_raw_keys()
        # Map key -> KeyMetrics
        self._metrics: Dict[str, KeyMetrics] = {k: KeyMetrics() for k in self._raw_keys}
        # Round‑robin index (protected by a lock for thread safety)
        self._rr_idx = 0
        self._rr_lock = threading.Lock()

    @property
    def keys(self) -> List[str]:
        """Expose keys list for backward compatibility with KeyPool."""
        return self._raw_keys

    @property
    def idx(self) -> int:
        """Expose current round-robin index."""
        return self._rr_idx

    def __len__(self) -> int:
        """Number of registered keys in pool."""
        return len(self._raw_keys)

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    def active_keys(self) -> List[str]:
        """Return keys that are not in cooldown."""
        return [k for k, m in self._metrics.items() if not m.is_cooldown()]

    def next_key(self) -> str:
        """Select the next healthy key using round‑robin.

        If **all** keys are in cooldown, we still return the *least‑recently*
        used key to avoid dead‑locking; the caller may treat this as a system
        error.
        """
        active = self.active_keys()
        if not active:
            if not self._raw_keys:
                return os.getenv("GEMINI_API_KEY", "")
            with self._rr_lock:
                key = self._raw_keys[self._rr_idx % len(self._raw_keys)]
                self._rr_idx += 1
                return key
        with self._rr_lock:
            key = active[self._rr_idx % len(active)]
            self._rr_idx += 1
            return key

    def add_keys(self, new_keys: List[str]) -> None:
        """Add additional API keys at runtime.

        Extends the raw key list and creates a ``KeyMetrics`` entry for each.
        ``new_keys`` may contain duplicates which are ignored.
        """
        for k in new_keys:
            clean = k.strip()
            if not clean or clean in self._raw_keys:
                continue
            self._raw_keys.append(clean)
            self._metrics[clean] = KeyMetrics()
        with self._rr_lock:
            self._rr_idx = 0

    # ---------------------------------------------------------------------
    # Metrics handling
    # ---------------------------------------------------------------------
    def record_success(self, key: str) -> None:
        if key in self._metrics:
            self._metrics[key].record(True)

    def record_failure(self, key: str, *, force_cooldown: bool = False) -> None:
        """Record a failure. ``force_cooldown`` is used for explicit 429/5xx."""
        if key not in self._metrics:
            return
        self._metrics[key].record(False)
        if force_cooldown:
            self._metrics[key].set_cooldown()
        elif self._metrics[key].should_cooldown():
            self._metrics[key].set_cooldown()

    # ---------------------------------------------------------------------
    # Decorator for wrapping LLM calls
    # ---------------------------------------------------------------------
    def track_error_rate(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Wrap an LLM‑calling function.

        The wrapped function must accept a ``key`` keyword argument. The decorator
        will inject the selected key, execute the call, and on failure automatically
        retry with the next healthy key (up to five attempts).
        """

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            max_attempts = 5
            last_exc: Exception | None = None
            for _ in range(max_attempts):
                key = self.next_key()
                kwargs["key"] = key
                try:
                    result = func(*args, **kwargs)
                    self.record_success(key)
                    return result
                except Exception as exc:
                    force = getattr(exc, "status_code", None) in {429, 500, 502, 503, 504}
                    self.record_failure(key, force_cooldown=bool(force))
                    last_exc = exc
                    continue
            raise last_exc or RuntimeError("All provider keys exhausted or failing")

        return wrapper

    # ---------------------------------------------------------------------
    # Diagnostic helper – used by monitoring dashboards or Loop 5
    # ---------------------------------------------------------------------
    def get_error_rate_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Return a snapshot of metrics for every key.

        Structure:
        ```json
        {
          "key‑string": {"total": 12, "errors": 3, "error_rate": 0.25, "cooldown": false}
        }
        ```
        """
        now = time.time()
        out: Dict[str, Dict[str, Any]] = {}
        for k, m in self._metrics.items():
            with m._lock:
                m.prune()
                total = len(m._events)
                errors = sum(1 for _, err in m._events if err)
                out[k] = {
                    "total": total,
                    "errors": errors,
                    "error_rate": errors / total if total else 0.0,
                    "cooldown": m.is_cooldown(),
                    "next_available_in": max(0.0, m._cooldown_until - now),
                }
        return out


# ---------------------------------------------------------------------------
# Export a ready‑to‑use singleton instance for the rest of the code‑base.
# ---------------------------------------------------------------------------
router = KeyPoolRouter.get_instance()
track_error_rate = router.track_error_rate
