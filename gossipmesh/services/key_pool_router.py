import collections
import functools
import inspect
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, List

from gossipmesh.core.config import (
    ERROR_RATE_THRESHOLD,
    KEY_COOLDOWN_SECONDS,
    MAX_KEY_RETRIES,
    parse_key_pool,
)


def _load_raw_keys() -> List[str]:
    """Discovers and deduplicates API keys from environment variables and local key files."""
    keys: List[str] = []

    def _append_keys(key_list: List[str]):
        for k in key_list:
            cleaned = k.strip()
            if cleaned and cleaned not in keys:
                keys.append(cleaned)

    # 1. Primary Gemini environment pools
    _append_keys(parse_key_pool(os.getenv("GEMINI_KEY_POOL", "")))
    for var in (
        "GEMINI_API_KEY",
        "GEMINI_ISSUE_KEY",
        "GEMINI_REVIEWER_KEY",
        "GEMINI_SOLVER_KEY",
    ):
        val = os.getenv(var, "").strip()
        if val and val not in keys:
            keys.append(val)

    # 2. Multi-provider pools
    for pool_var in (
        "OPENAI_API_KEYS",
        "GROQ_API_KEYS",
        "ANTHROPIC_API_KEYS",
        "DEEPSEEK_API_KEYS",
        "OPENROUTER_API_KEY",
        "HUGGINGFACE_API_KEY",
        "COHERE_API_KEY",
        "NVIDIA_API_KEY",
        "NVIDIA_API_KEY_2",
    ):
        raw_val = os.getenv(pool_var, "").strip()
        if raw_val:
            _append_keys(parse_key_pool(raw_val))

    # 3. Check gitignored local key files across common directories
    search_dirs = [
        Path("."),
        Path(__file__).resolve().parent,
        Path(__file__).resolve().parent.parent,
        Path(__file__).resolve().parent.parent.parent,
        Path.home(),
    ]
    for check_dir in search_dirs:
        # Check .gemini_keys
        gemini_file = check_dir / ".gemini_keys"
        if gemini_file.is_file():
            try:
                for line in gemini_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and line not in keys:
                        keys.append(line)
            except Exception:
                pass

        # Check .llm_keys
        llm_file = check_dir / ".llm_keys"
        if llm_file.is_file():
            try:
                for line in llm_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            _, val = line.split("=", 1)
                            val = val.strip()
                            if val and val not in keys:
                                keys.append(val)
                        elif line not in keys:
                            keys.append(line)
            except Exception:
                pass

    if not keys:
        is_test_env = bool(os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TEST_MODE") or "pytest" in sys.modules)
        if is_test_env:
            keys = ["dummy-test-key-1", "dummy-test-key-2"]
        else:
            print(
                "[KeyPoolRouter] Warning: 0 real keys configured in environment or key files.",
                file=sys.stderr,
                flush=True,
            )

    return keys


def mask_key(key: str) -> str:
    """Masks an API key for safe logging."""
    if not key:
        return "<empty>"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


class KeyMetrics:
    """Thread-safe rolling 5-minute error-rate tracker."""

    WINDOW: float = 300.0  # 5 minutes

    def __init__(self):
        self.lock = threading.Lock()
        self.events: collections.deque = collections.deque()

    def add(self, is_error: bool):
        now = time.time()
        with self.lock:
            self.events.append((now, is_error))
            cutoff = now - self.WINDOW
            while self.events and self.events[0][0] < cutoff:
                self.events.popleft()

    def error_rate(self) -> float:
        now = time.time()
        cutoff = now - self.WINDOW
        with self.lock:
            while self.events and self.events[0][0] < cutoff:
                self.events.popleft()
            if not self.events:
                return 0.0
            error_count = sum(1 for _, err in self.events if err)
            return error_count / len(self.events)

    def request_count(self) -> int:
        now = time.time()
        cutoff = now - self.WINDOW
        with self.lock:
            while self.events and self.events[0][0] < cutoff:
                self.events.popleft()
            return len(self.events)

    def reset(self):
        with self.lock:
            self.events.clear()


class KeyPoolRouter:
    """Multi-Key Pool Router with rolling error-rate circuit breaker and cooldown handling."""

    def __init__(self, initial_keys: List[str] | None = None):
        self.lock = threading.Lock()
        self.keys: List[str] = list(initial_keys) if initial_keys is not None else _load_raw_keys()
        self.metrics: dict[str, KeyMetrics] = {k: KeyMetrics() for k in self.keys}
        self.cooldowns: dict[str, float] = {}
        self.idx: int = 0

    def add_keys(self, new_keys: List[str]):
        """Dynamically adds new keys to the active pool."""
        with self.lock:
            for k in new_keys:
                clean = k.strip()
                if clean and clean not in self.keys:
                    self.keys.append(clean)
                    if clean not in self.metrics:
                        self.metrics[clean] = KeyMetrics()
                    print(
                        f"[KeyPoolRouter] Added new key to active pool (Total: {len(self.keys)})",
                        flush=True,
                    )

    def is_on_cooldown(self, key: str) -> bool:
        """Checks if key is on immediate or threshold cooldown."""
        now = time.time()
        if now < self.cooldowns.get(key, 0.0):
            return True

        # Check threshold cooldown (requests >= 4 and error_rate > ERROR_RATE_THRESHOLD)
        m = self.metrics.get(key)
        if m and m.request_count() >= 4 and m.error_rate() > ERROR_RATE_THRESHOLD:
            self.cooldowns[key] = now + KEY_COOLDOWN_SECONDS
            return True

        return False

    def next_key(self) -> str:
        """Returns the healthiest active key, rotating round-robin and skipping keys in cooldown."""
        with self.lock:
            if not self.keys:
                return ""

            num_keys = len(self.keys)
            # Try to find a key not on cooldown
            for _ in range(num_keys):
                candidate = self.keys[self.idx % num_keys]
                self.idx = (self.idx + 1) % num_keys
                if not self.is_on_cooldown(candidate):
                    return candidate

            # All keys are currently on cooldown: pick the key that expires earliest
            earliest_key = min(self.keys, key=lambda k: self.cooldowns.get(k, 0.0))
            return earliest_key

    def record(self, key: str, is_error: bool, immediate: bool = False):
        """Records a request outcome and applies cooldown if appropriate."""
        with self.lock:
            if key not in self.metrics:
                self.metrics[key] = KeyMetrics()
            self.metrics[key].add(is_error)

            now = time.time()
            if is_error and immediate:
                self.cooldowns[key] = now + KEY_COOLDOWN_SECONDS
            elif is_error:
                m = self.metrics[key]
                if m.request_count() >= 4 and m.error_rate() > ERROR_RATE_THRESHOLD:
                    self.cooldowns[key] = now + KEY_COOLDOWN_SECONDS

    def __len__(self) -> int:
        return len(self.keys)


# Singleton instances and aliases
KeyRouter = KeyPoolRouter
router = KeyPoolRouter()


def track_error_rate(fn: Callable | None = None, *, router_instance: KeyPoolRouter | None = None):
    """Decorator that wraps a function with automatic key rotation and error rate tracking.

    If the wrapped function fails:
    1. The exception and full traceback are logged to stderr (no silent swallowing).
    2. The failure is recorded in the key metrics.
    3. The next key is selected and the operation is retried up to MAX_KEY_RETRIES.
    """

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        accepts_api_key = "api_key" in sig.parameters

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            active_router = router_instance or router
            max_retries = MAX_KEY_RETRIES
            last_exception = None

            for attempt in range(1, max_retries + 1):
                key = active_router.next_key()
                if not key:
                    raise RuntimeError("No API keys available in KeyPoolRouter")

                # Propagate key via env vars
                os.environ["GEMINI_API_KEY"] = key
                os.environ["GEMINI_SOLVER_KEY"] = key
                os.environ["GEMINI_REVIEWER_KEY"] = key

                # Also inject via kwargs if the function signature accepts it
                call_kwargs = dict(kwargs)
                if accepts_api_key:
                    call_kwargs["api_key"] = key

                try:
                    res = func(*args, **call_kwargs)
                    active_router.record(key, is_error=False)
                    return res
                except Exception as e:
                    last_exception = e
                    err_msg = str(e).lower()
                    is_immediate = any(
                        term in err_msg for term in ("429", "503", "quota", "rate limit", "resourceexhausted")
                    )
                    active_router.record(key, is_error=True, immediate=is_immediate)

                    masked = mask_key(key)
                    print(
                        f"[KeyPoolRouter] Key {masked} failed: {e}. Rotating key (Attempt {attempt}/{max_retries})...",
                        file=sys.stderr,
                        flush=True,
                    )
                    traceback.print_exc(file=sys.stderr)
                    sys.stderr.flush()

            if last_exception:
                raise last_exception
            raise RuntimeError(f"All API keys exhausted after {max_retries} attempts")

        return wrapper

    if fn is not None:
        return decorator(fn)
    return decorator
