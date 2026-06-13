"""Tests for automated trending topic discovery."""

from __future__ import annotations

import asyncio
import importlib.util
import unittest

if not importlib.util.find_spec("feedparser") or not importlib.util.find_spec("sqlalchemy"):
    raise unittest.SkipTest("collector dependencies are required for trending tests")

from app.services.collector.trending import (
    GoogleTrendsProvider,
    TrendingDiscovery,
    TrendingTopic,
    extract_keywords,
)


class TrendingDiscoveryTest(unittest.TestCase):
    """Validate the discovery engine extension and ranking behavior."""

    def test_deduplication_merges_similar_topics(self) -> None:
        topics = TrendingDiscovery.deduplicate(
            [
                TrendingTopic("quake damage in city", ["quake", "damage", "city"], "google_trends", score=40),
                TrendingTopic("city quake damage update", ["city", "quake", "damage"], "gdelt", score=70),
                TrendingTopic("trade talks resume", ["trade", "talks", "resume"], "gdelt", score=30),
            ]
        )

        self.assertEqual(len(topics), 2)
        self.assertEqual(topics[0].score, 70)
        self.assertIn("google_trends", topics[0].source)
        self.assertIn("gdelt", topics[0].source)

    def test_google_trends_provider_extracts_keywords(self) -> None:
        self.assertEqual(GoogleTrendsProvider.parse_traffic("20,000+"), 20000)
        keywords = extract_keywords("Israel-Iran conflict latest update")

        self.assertIn("israel", keywords)
        self.assertIn("iran", keywords)
        self.assertIn("conflict", keywords)

    def test_stop_words_are_filtered(self) -> None:
        keywords = extract_keywords("The latest report and update on the summit")

        self.assertEqual(keywords, ["summit"])

    def test_register_provider_extends_discovery(self) -> None:
        class StaticProvider:
            async def fetch_trending(self) -> list[TrendingTopic]:
                return [TrendingTopic("port strike", ["port", "strike"], "manual", score=80)]

        discovery = TrendingDiscovery(providers=[])
        discovery.register_provider(StaticProvider())

        topics = asyncio.run(discovery.discover())

        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0].source, "manual")
        self.assertEqual(topics[0].keywords, ["port", "strike"])


if __name__ == "__main__":
    unittest.main()
