"""
Cache implementation for Tinkoff API client.
"""

import time
from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")


class Cache:
    """
    Simple in-memory cache with TTL support.
    
    Features:
    - TTL-based invalidation
    - Hit/miss ratio tracking
    - Async support
    """

    def __init__(self, ttl: int = 300):  # 5 minutes default TTL
        self.ttl = ttl
        self.data: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}
        
        # Statistics
        self.hits = 0
        self.misses = 0

    def _is_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self.timestamps:
            return False
        return time.time() - self.timestamps[key] < self.ttl

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key in self.data and self._is_valid(key):
            self.hits += 1
            return self.data[key]
        
        self.misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self.data[key] = value
        self.timestamps[key] = time.time()

    def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
        """
        if key in self.data:
            del self.data[key]
            del self.timestamps[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self.data.clear()
        self.timestamps.clear()

    async def get_or_set(self, key: str, fetch_func: Callable[[], T]) -> T:
        """
        Get value from cache or fetch and cache it if not found.
        
        Args:
            key: Cache key
            fetch_func: Async function to fetch value if not in cache
            
        Returns:
            Cached or fetched value
        """
        value = self.get(key)
        if value is not None:
            return value

        value = await fetch_func()
        self.set(key, value)
        return value

    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.hit_ratio,
            "size": len(self.data),
        } 