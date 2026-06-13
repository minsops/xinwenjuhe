"""Tests for pluggable source collector registry."""

from __future__ import annotations

import asyncio
import importlib.util
import unittest
import uuid
from unittest.mock import patch

if not importlib.util.find_spec("sqlalchemy"):
    raise unittest.SkipTest("SQLAlchemy is required for registry tests")

from app.models.source import Source
from app.schemas.article import RawArticle
from app.services.collector.ingestion import ArticleIngestionService
from app.services.collector.registry import SourceCollectorRegistry, get_registry


class CollectorRegistryTest(unittest.TestCase):
    """Validate default and custom collector registration."""

    def test_default_registry_supports_builtin_source_types(self) -> None:
        supported = get_registry().supported_types()

        self.assertIn("rss", supported)
        self.assertIn("api", supported)
        self.assertIn("scraper", supported)

    def test_custom_collector_can_be_registered(self) -> None:
        registry = SourceCollectorRegistry()
        registry.register("podcast", StaticCollector("podcast"))

        self.assertEqual(registry.supported_types(), ["podcast"])
        self.assertIsNotNone(registry.get("podcast"))

    def test_ingestion_uses_registered_collector_without_branch_change(self) -> None:
        registry = SourceCollectorRegistry()
        registry.register("custom", StaticCollector("custom"))
        source = _source("custom")

        with patch("app.services.collector.ingestion.get_registry", return_value=registry):
            rows = asyncio.run(ArticleIngestionService(None)._fetch_source_articles(source))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].title_original, "custom story")


class StaticCollector:
    """Collector double for custom feed types."""

    def __init__(self, label: str) -> None:
        self.label = label

    async def collect(self, source: Source) -> list[RawArticle]:
        return [
            RawArticle(
                external_url=f"https://example.test/{self.label}",
                title_original=f"{self.label} story",
                content_original="full text",
                language=source.language,
            )
        ]


def _source(feed_type: str) -> Source:
    return Source(
        id=uuid.uuid4(),
        name="Custom",
        country="US",
        region="north_america",
        language="en",
        feed_type=feed_type,
        feed_url="https://example.test/feed",
    )


if __name__ == "__main__":
    unittest.main()
