"""
Tests for Tinkoff API cache.
"""

import asyncio
import time
import pytest

from src.services.tinkoff.cache import Cache


@pytest.fixture
def cache():
    """Create test cache instance."""
    return Cache(ttl=1)  # 1 second TTL for faster testing


def test_cache_set_get():
    """Test basic cache set/get operations."""
    cache = Cache()
    cache.set("test", "value")
    assert cache.get("test") == "value"


def test_cache_ttl():
    """Test cache TTL expiration."""
    cache = Cache(ttl=1)
    cache.set("test", "value")
    
    # Value should be available immediately
    assert cache.get("test") == "value"
    
    # Wait for TTL to expire
    time.sleep(1.1)
    assert cache.get("test") is None


def test_cache_delete():
    """Test cache entry deletion."""
    cache = Cache()
    cache.set("test", "value")
    assert cache.get("test") == "value"
    
    cache.delete("test")
    assert cache.get("test") is None


def test_cache_clear():
    """Test cache clearing."""
    cache = Cache()
    cache.set("test1", "value1")
    cache.set("test2", "value2")
    
    cache.clear()
    assert cache.get("test1") is None
    assert cache.get("test2") is None


def test_cache_hit_ratio():
    """Test cache hit ratio calculation."""
    cache = Cache()
    
    # Miss (key doesn't exist)
    cache.get("test")
    assert cache.hit_ratio == 0.0
    
    # Set and hit
    cache.set("test", "value")
    cache.get("test")
    assert cache.hit_ratio == 0.5
    
    # Another hit
    cache.get("test")
    assert cache.hit_ratio == 2/3


def test_cache_stats():
    """Test cache statistics."""
    cache = Cache()
    
    # Initial stats
    stats = cache.stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_ratio"] == 0.0
    assert stats["size"] == 0
    
    # Add some data and access it
    cache.set("test", "value")
    cache.get("test")  # Hit
    cache.get("missing")  # Miss
    
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_ratio"] == 0.5
    assert stats["size"] == 1


@pytest.mark.asyncio
async def test_cache_get_or_set():
    """Test async get_or_set operation."""
    cache = Cache()
    
    # Mock async fetch function
    async def fetch_value():
        return "fetched_value"
    
    # First call should fetch
    value = await cache.get_or_set("test", fetch_value)
    assert value == "fetched_value"
    assert cache.stats()["misses"] == 1
    
    # Second call should use cache
    value = await cache.get_or_set("test", fetch_value)
    assert value == "fetched_value"
    assert cache.stats()["hits"] == 1


@pytest.mark.asyncio
async def test_cache_get_or_set_concurrent():
    """Test concurrent cache access."""
    cache = Cache()
    fetch_count = 0
    
    async def fetch_value():
        nonlocal fetch_count
        fetch_count += 1
        await asyncio.sleep(0.1)  # Simulate slow operation
        return "fetched_value"
    
    # Make concurrent requests
    tasks = [
        cache.get_or_set("test", fetch_value)
        for _ in range(5)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # All results should be the same
    assert all(r == "fetched_value" for r in results)
    # Should only fetch once
    assert fetch_count == 1
    # Stats should show one miss and four hits
    assert cache.stats()["misses"] == 1
    assert cache.stats()["hits"] == 4 