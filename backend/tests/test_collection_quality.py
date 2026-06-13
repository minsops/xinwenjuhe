"""Tests for collection quality metrics."""

from __future__ import annotations

import asyncio
import importlib.util
import unittest
import uuid
from unittest.mock import patch

if not importlib.util.find_spec("redis") or not importlib.util.find_spec("sqlalchemy"):
    raise unittest.SkipTest("Redis and SQLAlchemy are required for collection quality tests")

from app.models.source import Source
from app.schemas.article import RawArticle
from app.services.collector.quality import (
    COLLECTION_METRICS_HISTORY_KEY,
    build_collection_metrics,
    list_collection_metrics,
    record_collection_metrics,
)


class CollectionQualityTest(unittest.TestCase):
    """Validate source collection quality calculations and Redis persistence."""

    def test_low_fulltext_success_rate_is_unhealthy(self) -> None:
        metrics = build_collection_metrics(
            _source(),
            [
                _raw_article("https://example.test/a", "x" * 250),
                _raw_article("https://example.test/b", "short"),
                _raw_article("https://example.test/c", ""),
            ],
            {"skipped": 1},
        )
        payload = metrics.to_dict()

        self.assertEqual(payload["articles_fetched"], 3)
        self.assertEqual(payload["articles_with_fulltext"], 1)
        self.assertEqual(payload["articles_empty_content"], 1)
        self.assertEqual(payload["articles_short_content"], 1)
        self.assertEqual(payload["articles_deduplicated"], 1)
        self.assertEqual(payload["fulltext_success_rate"], 0.333)
        self.assertFalse(payload["is_healthy"])

    def test_record_and_list_collection_metrics_use_history_key(self) -> None:
        fake = FakeRedis()
        metrics = build_collection_metrics(_source(), [_raw_article("https://example.test/a", "x" * 250)])

        with patch("app.services.collector.quality.Redis.from_url", return_value=fake):
            asyncio.run(record_collection_metrics(metrics))
            rows = asyncio.run(list_collection_metrics(limit=5))

        self.assertEqual(fake.history_key, COLLECTION_METRICS_HISTORY_KEY)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["is_healthy"])
        self.assertEqual(rows[0]["fulltext_success_rate"], 1.0)


class FakeRedis:
    """Minimal async Redis double for metric recording."""

    def __init__(self) -> None:
        self.rows: list[str] = []
        self.history_key = ""

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.last_key = key
        self.last_ttl = ttl
        self.last_value = value

    async def lpush(self, key: str, value: str) -> None:
        self.history_key = key
        self.rows.insert(0, value)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        self.rows = self.rows[start : end + 1]

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        return self.rows[start : end + 1]

    async def aclose(self) -> None:
        return None


def _source() -> Source:
    return Source(
        id=uuid.uuid4(),
        name="Example",
        country="US",
        region="north_america",
        language="en",
        feed_type="rss",
        feed_url="https://example.test/rss",
    )


def _raw_article(url: str, content: str) -> RawArticle:
    return RawArticle(
        external_url=url,
        title_original="Example story",
        content_original=content,
        language="en",
    )


if __name__ == "__main__":
    unittest.main()
