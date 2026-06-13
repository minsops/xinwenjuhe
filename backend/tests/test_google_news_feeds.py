"""Regression tests for multilingual Google News feed coverage."""

from __future__ import annotations

import asyncio
import base64
from importlib.util import find_spec
from types import SimpleNamespace
from unittest.mock import patch
import unittest

if not find_spec("feedparser"):
    raise unittest.SkipTest("collector dependencies are not installed")

from app.services.collector.google_news import GoogleNewsCollector
from app.services.collector.rss_collector import RSSCollector


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
        self.assertEqual(
            GoogleNewsCollector.feed_for_language("en"),
            GoogleNewsCollector.REGION_FEEDS["en-US"],
        )
        self.assertEqual(
            GoogleNewsCollector.feed_for_language("pt"),
            GoogleNewsCollector.REGION_FEEDS["pt-BR"],
        )
        self.assertEqual(
            GoogleNewsCollector.feed_for_language("xx"),
            GoogleNewsCollector.REGION_FEEDS["en-US"],
        )

    def test_decodes_google_news_rss_article_url_to_publisher_url(self) -> None:
        publisher_url = "https://publisher.test/world/story?id=42&lang=en"
        token = base64.urlsafe_b64encode(f'\x08\x13"{publisher_url}'.encode()).decode().rstrip("=")
        google_url = f"https://news.google.com/rss/articles/{token}?oc=5"

        decoded = GoogleNewsCollector.decode_google_news_url(google_url)

        self.assertEqual(decoded, publisher_url)

    def test_search_event_fetches_fulltext_from_decoded_publisher_url(self) -> None:
        publisher_url = "https://publisher.test/full"
        token = base64.urlsafe_b64encode(f'\x08\x13"{publisher_url}'.encode()).decode().rstrip("=")
        entries = [
            SimpleNamespace(
                link=f"https://news.google.com/rss/articles/{token}?oc=5",
                title="Full",
                summary="short",
                published=None,
            ),
        ]
        requested_urls: list[str] = []

        async def fetch_full_content(self, url: str) -> str:
            requested_urls.append(url)
            return "Full article body. " * 20

        with (
            patch(
                "app.services.collector.google_news.feedparser.parse",
                return_value=SimpleNamespace(entries=entries),
            ),
            patch("app.services.collector.google_news.httpx.AsyncClient", FakeAsyncClient),
            patch.object(RSSCollector, "fetch_full_content", fetch_full_content),
        ):
            articles = asyncio.run(GoogleNewsCollector().search_event("query", "en-US"))

        self.assertEqual(requested_urls, [publisher_url])
        self.assertEqual(articles[0].external_url, publisher_url)
        self.assertGreaterEqual(len(articles[0].content_original), GoogleNewsCollector.MIN_FULLTEXT_LENGTH)

    def test_search_event_keeps_only_fulltext_articles(self) -> None:
        entries = [
            SimpleNamespace(
                link="https://news.google.com/full",
                title="Full",
                summary="short",
                published=None,
            ),
            SimpleNamespace(
                link="https://news.google.com/short",
                title="Short",
                summary="short",
                published=None,
            ),
            SimpleNamespace(
                link="https://news.google.com/fail",
                title="Fail",
                summary="short",
                published=None,
            ),
        ]
        full_body = "Full article body. " * 20

        async def resolve_link(self, url: str) -> str:
            return url.replace("https://news.google.com/", "https://publisher.test/")

        async def fetch_full_content(self, url: str) -> str:
            if url.endswith("/full"):
                return full_body
            if url.endswith("/short"):
                return "too short"
            raise RuntimeError("fetch failed")

        with (
            patch(
                "app.services.collector.google_news.feedparser.parse",
                return_value=SimpleNamespace(entries=entries),
            ),
            patch("app.services.collector.google_news.httpx.AsyncClient", FakeAsyncClient),
            patch.object(GoogleNewsCollector, "resolve_google_link", resolve_link),
            patch.object(RSSCollector, "fetch_full_content", fetch_full_content),
        ):
            articles = asyncio.run(GoogleNewsCollector().search_event("query", "en-US"))

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].external_url, "https://publisher.test/full")
        self.assertEqual(articles[0].content_original, full_body)
        self.assertGreaterEqual(
            len(articles[0].content_original),
            GoogleNewsCollector.MIN_FULLTEXT_LENGTH,
        )

    def test_search_event_fast_mode_can_return_feed_summaries(self) -> None:
        entries = [
            SimpleNamespace(
                link="https://news.google.com/summary",
                title="Summary",
                summary="feed summary",
                published=None,
            ),
        ]

        async def resolve_link(self, url: str) -> str:
            return url.replace("https://news.google.com/", "https://publisher.test/")

        with (
            patch(
                "app.services.collector.google_news.feedparser.parse",
                return_value=SimpleNamespace(entries=entries),
            ),
            patch("app.services.collector.google_news.httpx.AsyncClient", FakeAsyncClient),
            patch.object(GoogleNewsCollector, "resolve_google_link", resolve_link),
        ):
            articles = asyncio.run(
                GoogleNewsCollector().search_event("query", "en-US", fetch_fulltext=False)
            )

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].content_original, "feed summary")


class FakeResponse:
    """Minimal response for Google News RSS fetches."""

    content = b"<rss />"

    def raise_for_status(self) -> None:
        return None


class FakeAsyncClient:
    """Minimal async context manager replacing httpx.AsyncClient."""

    def __init__(self, *args, **kwargs) -> None:
        return None

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, *args, **kwargs) -> FakeResponse:
        return FakeResponse()


if __name__ == "__main__":
    unittest.main()
