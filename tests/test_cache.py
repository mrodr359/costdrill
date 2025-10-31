"""
Tests for caching utilities.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from costdrill.utils.cache import SimpleCache, generate_cache_key


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_cache_initialization(temp_cache_dir):
    """Test cache initialization."""
    cache = SimpleCache(cache_dir=temp_cache_dir, default_ttl=3600)
    assert cache.cache_dir == temp_cache_dir
    assert cache.default_ttl == 3600
    assert cache.cache_dir.exists()


def test_cache_set_and_get(temp_cache_dir):
    """Test basic cache set and get operations."""
    cache = SimpleCache(cache_dir=temp_cache_dir)

    # Set a value
    cache.set("test_key", "test_value")

    # Get the value
    value = cache.get("test_key")
    assert value == "test_value"


def test_cache_miss(temp_cache_dir):
    """Test cache miss returns None."""
    cache = SimpleCache(cache_dir=temp_cache_dir)
    value = cache.get("nonexistent_key")
    assert value is None


def test_cache_expiration(temp_cache_dir):
    """Test cache expiration."""
    cache = SimpleCache(cache_dir=temp_cache_dir, default_ttl=1)

    # Set a value with 1 second TTL
    cache.set("expire_key", "expire_value", ttl=0)

    # Value should be expired immediately
    value = cache.get("expire_key")
    assert value is None


def test_cache_delete(temp_cache_dir):
    """Test cache deletion."""
    cache = SimpleCache(cache_dir=temp_cache_dir)

    # Set and verify
    cache.set("delete_key", "delete_value")
    assert cache.get("delete_key") == "delete_value"

    # Delete and verify
    cache.delete("delete_key")
    assert cache.get("delete_key") is None


def test_cache_clear(temp_cache_dir):
    """Test clearing all cache."""
    cache = SimpleCache(cache_dir=temp_cache_dir)

    # Set multiple values
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    # Clear all
    cache.clear()

    # Verify all are gone
    assert cache.get("key1") is None
    assert cache.get("key2") is None
    assert cache.get("key3") is None


def test_cache_complex_objects(temp_cache_dir):
    """Test caching complex Python objects."""
    cache = SimpleCache(cache_dir=temp_cache_dir)

    # Test with dict
    data = {"name": "test", "value": 123, "items": [1, 2, 3]}
    cache.set("dict_key", data)
    cached_data = cache.get("dict_key")
    assert cached_data == data

    # Test with list
    list_data = [1, 2, 3, "four", {"five": 5}]
    cache.set("list_key", list_data)
    cached_list = cache.get("list_key")
    assert cached_list == list_data


def test_generate_cache_key():
    """Test cache key generation."""
    # Test with positional args
    key1 = generate_cache_key("arg1", "arg2", 123)
    key2 = generate_cache_key("arg1", "arg2", 123)
    assert key1 == key2

    # Test with keyword args
    key3 = generate_cache_key(name="test", value=456)
    key4 = generate_cache_key(name="test", value=456)
    assert key3 == key4

    # Test with mixed args
    key5 = generate_cache_key("arg1", name="test", value=789)
    key6 = generate_cache_key("arg1", name="test", value=789)
    assert key5 == key6

    # Different args should produce different keys
    key7 = generate_cache_key("different")
    assert key1 != key7


def test_cache_clear_expired(temp_cache_dir):
    """Test clearing only expired entries."""
    cache = SimpleCache(cache_dir=temp_cache_dir, default_ttl=3600)

    # Set values with different TTLs
    cache.set("long_lived", "value1", ttl=3600)
    cache.set("expired", "value2", ttl=0)

    # Clear expired
    deleted = cache.clear_expired()
    assert deleted >= 1

    # Long-lived should still exist
    assert cache.get("long_lived") == "value1"

    # Expired should be gone
    assert cache.get("expired") is None
