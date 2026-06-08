"""Regression tests for multilingual Google News feed coverage."""

from __future__ import annotations

from importlib.util import find_spec
import unittest

if not find_spec("feedparser"):
    raise unittest.SkipTest("collector dependencies are not installed")

from app.services.collector.google_news import GoogleNewsCollector


class GoogleNewsFeedsTest(unittest.TestCase):
    """Validate the documented 60+ Google News edition coverage."""

    def test_region_feeds_cover_sixty_plus_editions(self) -> None:
        feeds = GoogleNewsCollector.REGION_FEEDS

        self.assertGreaterEqual(len(feeds), 60)
        self.assertEqual(len(set(feeds.values())), len(feeds))
        for url in feeds.values():
            self.assertIn("news.google.com/rss", url)
            self.assertIn("hl=", url)
            self.assertIn("gl=", url)
            self.assertIn("ceid=", url)

    def test_base_language_falls_back_to_matching_edition(self) -> None:
        self.assertEqual(GoogleNewsCollector.feed_for_language("en"), GoogleNewsCollector.REGION_FEEDS["en-US"])
        self.assertEqual(GoogleNewsCollector.feed_for_language("pt"), GoogleNewsCollector.REGION_FEEDS["pt-BR"])
        self.assertEqual(GoogleNewsCollector.feed_for_language("xx"), GoogleNewsCollector.REGION_FEEDS["en-US"])


if __name__ == "__main__":
    unittest.main()
