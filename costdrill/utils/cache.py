"""
Caching utilities for API responses.
"""

import hashlib
import json
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SimpleCache:
    """Simple file-based cache with TTL support."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        default_ttl: int = 3600,
    ):
        """
        Initialize cache.

        Args:
            cache_dir: Directory for cache files (defaults to ~/.costdrill/cache)
            default_ttl: Default time-to-live in seconds (default: 1 hour)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".costdrill" / "cache"

        self.cache_dir = cache_dir
        self.default_ttl = default_ttl

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Cache directory: {self.cache_dir}")

    def _get_cache_key(self, key: str) -> str:
        """
        Generate cache key hash.

        Args:
            key: Original key

        Returns:
            Hashed key for filename
        """
        return hashlib.sha256(key.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """
        Get cache file path for a key.

        Args:
            key: Cache key

        Returns:
            Path to cache file
        """
        cache_key = self._get_cache_key(key)
        return self.cache_dir / f"{cache_key}.cache"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            logger.debug(f"Cache miss: {key}")
            return None

        try:
            with open(cache_path, "rb") as f:
                cache_data = pickle.load(f)

            # Check if expired
            expiry = cache_data.get("expiry")
            if expiry and datetime.now() > expiry:
                logger.debug(f"Cache expired: {key}")
                cache_path.unlink()  # Delete expired cache
                return None

            logger.debug(f"Cache hit: {key}")
            return cache_data.get("value")

        except (pickle.PickleError, EOFError, OSError) as e:
            logger.warning(f"Error reading cache for {key}: {e}")
            # Delete corrupted cache file
            if cache_path.exists():
                cache_path.unlink()
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        if ttl is None:
            ttl = self.default_ttl

        cache_path = self._get_cache_path(key)
        expiry = datetime.now() + timedelta(seconds=ttl)

        cache_data = {
            "value": value,
            "expiry": expiry,
            "created_at": datetime.now(),
        }

        try:
            with open(cache_path, "wb") as f:
                pickle.dump(cache_data, f)
            logger.debug(f"Cached: {key} (TTL: {ttl}s)")

        except (pickle.PickleError, OSError) as e:
            logger.warning(f"Error writing cache for {key}: {e}")

    def delete(self, key: str) -> None:
        """
        Delete value from cache.

        Args:
            key: Cache key
        """
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
            logger.debug(f"Deleted cache: {key}")

    def clear(self) -> None:
        """Clear all cache files."""
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                cache_file.unlink()
            except OSError as e:
                logger.warning(f"Error deleting cache file {cache_file}: {e}")

        logger.info("Cache cleared")

    def clear_expired(self) -> int:
        """
        Clear all expired cache files.

        Returns:
            Number of files deleted
        """
        deleted = 0
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with open(cache_file, "rb") as f:
                    cache_data = pickle.load(f)

                expiry = cache_data.get("expiry")
                if expiry and datetime.now() > expiry:
                    cache_file.unlink()
                    deleted += 1

            except (pickle.PickleError, EOFError, OSError):
                # Delete corrupted files
                cache_file.unlink()
                deleted += 1

        logger.info(f"Cleared {deleted} expired cache files")
        return deleted


def generate_cache_key(*args: Any, **kwargs: Any) -> str:
    """
    Generate cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    # Convert args and kwargs to JSON string for consistent hashing
    key_data = {
        "args": [str(arg) for arg in args],
        "kwargs": {k: str(v) for k, v in sorted(kwargs.items())},
    }
    return json.dumps(key_data, sort_keys=True)
