"""SQLite-based cache with TTL for API responses."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / ".copilot-pulse" / "cache.db"


class CacheStore:
    """Local SQLite cache for API responses with configurable TTL.

    Args:
        ttl_hours: Time-to-live for cache entries in hours.
        db_path: Path to the SQLite database file.
    """

    def __init__(self, ttl_hours: int = 6, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.ttl_seconds = ttl_hours * 3600
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._init_db()

    def _init_db(self) -> None:
        """Create the cache table if it doesn't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        self._conn.commit()

    def get(self, key: str) -> Any | None:
        """Retrieve a cached value if it exists and is not expired.

        Args:
            key: Cache key.

        Returns:
            Deserialized value or None if miss/expired.
        """
        cursor = self._conn.execute(
            "SELECT value, created_at FROM cache WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        if row is None:
            return None

        value_str, created_at = row
        if time.time() - created_at > self.ttl_seconds:
            self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()
            logger.debug("Cache expired for key: %s", key)
            return None

        logger.debug("Cache hit for key: %s", key)
        return json.loads(value_str)

    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache.

        Args:
            key: Cache key.
            value: JSON-serializable value.
        """
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
            (key, json.dumps(value, default=str), time.time()),
        )
        self._conn.commit()
        logger.debug("Cached key: %s", key)

    def delete_prefix(self, prefix: str) -> int:
        """Remove all cache entries whose key starts with *prefix*.

        Args:
            prefix: Key prefix to match (e.g. ``"maturity:"``).

        Returns:
            Number of entries removed.
        """
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM cache WHERE key LIKE ?", (prefix + "%",)
        )
        count = cursor.fetchone()[0]
        self._conn.execute("DELETE FROM cache WHERE key LIKE ?", (prefix + "%",))
        self._conn.commit()
        logger.info("Deleted %d cache entries with prefix '%s'", count, prefix)
        return count

    def clear(self) -> int:
        """Remove all cache entries.

        Returns:
            Number of entries removed.
        """
        cursor = self._conn.execute("SELECT COUNT(*) FROM cache")
        count = cursor.fetchone()[0]
        self._conn.execute("DELETE FROM cache")
        self._conn.commit()
        logger.info("Cleared %d cache entries", count)
        return count

    def purge_expired(self) -> int:
        """Remove only expired entries.

        Returns:
            Number of entries purged.
        """
        cutoff = time.time() - self.ttl_seconds
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM cache WHERE created_at < ?", (cutoff,)
        )
        count = cursor.fetchone()[0]
        self._conn.execute("DELETE FROM cache WHERE created_at < ?", (cutoff,))
        self._conn.commit()
        logger.info("Purged %d expired cache entries", count)
        return count

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with total entries, expired count, and DB size.
        """
        cutoff = time.time() - self.ttl_seconds
        total = self._conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        expired = self._conn.execute(
            "SELECT COUNT(*) FROM cache WHERE created_at < ?", (cutoff,)
        ).fetchone()[0]
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "total_entries": total,
            "expired_entries": expired,
            "valid_entries": total - expired,
            "db_size_bytes": db_size,
            "ttl_hours": self.ttl_seconds // 3600,
        }

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
