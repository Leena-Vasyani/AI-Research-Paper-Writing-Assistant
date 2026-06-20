"""
Hybrid cache layer: Redis (if available) -> in-memory LRU + TTL fallback.

Used by KeywordAgent, QueryAgent, and RetrievalAgent to avoid redundant
LLM/embedding calls and expensive API round-trips.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

_DEFAULT_TTL_SECONDS = int(os.getenv("AGENT_CACHE_TTL_SECONDS", "3600"))
_DEFAULT_MAX_SIZE = int(os.getenv("AGENT_CACHE_MAX_SIZE", "256"))

# ---------------------------------------------------------------------------
# Optional Redis backend
# ---------------------------------------------------------------------------

try:
    import redis as _redis_lib
except Exception:
    _redis_lib = None  # type: ignore[assignment]


class _RedisCache:
    """Thin wrapper around redis-py with JSON serialization."""

    def __init__(self, ttl: int = _DEFAULT_TTL_SECONDS):
        self._ttl = ttl
        self._client: Any = None
        self._enabled = False
        self._init()

    def _init(self) -> None:
        if _redis_lib is None:
            return
        redis_url = os.getenv("REDIS_URL", "").strip()
        if not redis_url:
            return
        try:
            self._client = _redis_lib.from_url(redis_url, decode_responses=True)
            self._client.ping()
            self._enabled = True
            print(f"   [OK] Redis cache connected: {redis_url}")
        except Exception as exc:
            print(f"   [!] Redis connection failed: {exc}; falling back to in-memory")
            self._client = None
            self._enabled = False

    def get(self, key: str) -> Any:
        if not self._enabled or self._client is None:
            return None
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            return None

    def set(self, key: str, value: Any) -> None:
        if not self._enabled or self._client is None:
            return
        try:
            payload = json.dumps(value, default=str)
            self._client.setex(key, self._ttl, payload)
        except Exception:
            pass

    def stats(self) -> dict:
        if not self._enabled or self._client is None:
            return {"enabled": False}
        try:
            info = self._client.info("memory")
            return {
                "enabled": True,
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "keys": self._client.dbsize(),
            }
        except Exception:
            return {"enabled": True}


# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expires_at = time.time() + ttl


class TTLCache:
    """Thread-safe (via GIL) in-memory LRU cache with TTL eviction."""

    def __init__(self, maxsize: int = _DEFAULT_MAX_SIZE, ttl: int = _DEFAULT_TTL_SECONDS):
        self._ttl = ttl
        self._maxsize = maxsize
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()

    def _make_key(self, *args: Any, **kwargs: Any) -> str:
        """Deterministic hash key from args/kwargs."""
        try:
            payload = repr((args, sorted(kwargs.items())))
        except Exception:
            payload = str((args, kwargs))
        return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()[:32]

    def get(self, key: str) -> Any:
        """Retrieve value if present and not expired; otherwise return None."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() > entry.expires_at:
            self._cache.pop(key, None)
            return None
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return entry.value

    def set(self, key: str, value: Any) -> None:
        """Store value with TTL. Evicts oldest if over capacity."""
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = _CacheEntry(value, self._ttl)
            return

        if len(self._cache) >= self._maxsize:
            # Evict oldest (first item)
            self._cache.popitem(last=False)

        self._cache[key] = _CacheEntry(value, self._ttl)

    def cached(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator that caches the function result by its arguments."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            cache_key = self._make_key(func.__name__, *args, **kwargs)
            cached_value = self.get(cache_key)
            if cached_value is not None:
                return cached_value
            result = func(*args, **kwargs)
            self.set(cache_key, result)
            return result

        return wrapper

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def stats(self) -> dict:
        """Return basic cache stats."""
        now = time.time()
        expired = sum(1 for e in self._cache.values() if now > e.expires_at)
        return {
            "size": len(self._cache),
            "maxsize": self._maxsize,
            "ttl_seconds": self._ttl,
            "expired_entries": expired,
        }


class HybridCache:
    """
    Two-tier cache: Redis (shared/persistent) -> in-memory (fast/local).
    Reads check Redis first, then memory.
    Writes go to both layers.
    """

    def __init__(self, maxsize: int = _DEFAULT_MAX_SIZE, ttl: int = _DEFAULT_TTL_SECONDS):
        self._memory = TTLCache(maxsize=maxsize, ttl=ttl)
        self._redis = _RedisCache(ttl=ttl)

    def get(self, key: str) -> Any:
        # Fast path: memory
        val = self._memory.get(key)
        if val is not None:
            return val
        # Slow path: redis -> backfill memory
        val = self._redis.get(key)
        if val is not None:
            self._memory.set(key, val)
            return val
        return None

    def set(self, key: str, value: Any) -> None:
        self._memory.set(key, value)
        self._redis.set(key, value)

    def cached(self, func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            cache_key = self._memory._make_key(func.__name__, *args, **kwargs)
            cached_value = self.get(cache_key)
            if cached_value is not None:
                return cached_value
            result = func(*args, **kwargs)
            self.set(cache_key, result)
            return result
        return wrapper

    def clear(self) -> None:
        self._memory.clear()

    def stats(self) -> dict:
        return {
            "memory": self._memory.stats(),
            "redis": self._redis.stats(),
        }


# Global singleton cache instances
keyword_cache = HybridCache(maxsize=_DEFAULT_MAX_SIZE, ttl=_DEFAULT_TTL_SECONDS)
query_cache = HybridCache(maxsize=_DEFAULT_MAX_SIZE, ttl=_DEFAULT_TTL_SECONDS)
retrieval_cache = HybridCache(maxsize=512, ttl=_DEFAULT_TTL_SECONDS)
