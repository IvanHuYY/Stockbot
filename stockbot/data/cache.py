"""Simple TTL-based cache for market data."""

from __future__ import annotations

import time
from typing import Any

import structlog

logger = structlog.get_logger()


class TTLCache:
    """In-memory cache with time-to-live expiration."""

    def __init__(self, default_ttl: int = 300) -> None:
        self._cache: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Get a value if it exists and hasn't expired."""
        if key in self._cache:
            value, expires_at = self._cache[key]
            if time.time() < expires_at:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value with optional custom TTL."""
        expires_at = time.time() + (ttl or self._default_ttl)
        self._cache[key] = (value, expires_at)

    def invalidate(self, key: str) -> None:
        """Remove a specific key."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    def cleanup(self) -> int:
        """Remove all expired entries. Returns count of removed items."""
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if now >= exp]
        for k in expired:
            del self._cache[k]
        return len(expired)
