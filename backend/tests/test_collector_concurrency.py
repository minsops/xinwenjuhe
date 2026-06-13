"""Collector concurrency and per-domain throttling tests."""

from __future__ import annotations

import asyncio
from importlib.util import find_spec
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import uuid

from app.services.collector.rate_limiter import DomainRateLimiter

if find_spec("feedparser") and find_spec("trafilatura"):
    from app.services.collector.rss_collector import RSSCollector
else:
    RSSCollector = None
RSSBase = RSSCollector if RSSCollector is not None else object

if find_spec("bs4") and find_spec("scrapy"):
    from app.services.collector.scraper import WebScraper
else:
    WebScraper = None
WebScraperBase = WebScraper if WebScraper is not None else object


class CollectorConcurrencyTest(unittest.TestCase):
    """Validate documented collector concurrency contracts without network access."""

    def test_domain_limiter_spaces_same_domain_starts(self) -> None:
        async def run_case() -> list[float]:
            limiter = DomainRateLimiter(0.01)
            loop = asyncio.get_running_loop()

            async def mark(path: str) -> float:
                await limiter.wait(f"https://example.test/{path}")
                return loop.time()

            return await asyncio.gather(*(mark(str(index)) for index in range(4)))

        starts = asyncio.run(run_case())
        gaps = [right - left for left, right in zip(starts, starts[1:])]

        self.assertTrue(all(gap >= 0.008 for gap in gaps), gaps)

    def test_rss_fulltext_fetch_is_concurrent_and_domain_spaced(self) -> None:
        if RSSCollector is None:
            raise unittest.SkipTest("RSS collector dependencies are not installed")

        async def run_case() -> RecordingRSSCollector:
            collector = RecordingRSSCollector()
            source = SimpleNamespace(
                id=uuid.uuid4(),
                feed_url="https://feed.test/rss",
                language="en",
                last_collected_at=None,
            )
            entries = [
                SimpleNamespace(
                    link=f"https://news.test/article-{index}",
                    title=f"Article {index}",
                    summary="summary",
                    published=None,
                    author=None,
                    id=str(index),
                )
                for index in range(4)
            ]
            with (
                patch(
                    "app.services.collector.rss_collector.feedparser.parse",
                    return_value=SimpleNamespace(entries=entries),
                ),
                patch("app.services.collector.rss_collector.httpx.AsyncClient", FakeAsyncClient),
            ):
                articles = await collector.fetch_feed(source)
            self.assertEqual(len(articles), 4)
            return collector

        collector = asyncio.run(run_case())

        self.assertGreaterEqual(collector.max_active, 2)
        self.assertLessEqual(collector.max_active, collector.FULLTEXT_CONCURRENCY)
        self.assert_domain_spaced(collector.starts)

    def test_scraper_article_fetch_is_concurrent_and_domain_spaced(self) -> None:
        if WebScraper is None:
            raise unittest.SkipTest("scraper dependencies are not installed")

        async def run_case() -> RecordingWebScraper:
            scraper = RecordingWebScraper()
            source = SimpleNamespace(
                id=uuid.uuid4(),
                name="Test Source",
                language="en",
                scraper_config={
                    "list_url": "https://site.test/list",
                    "article_selector": "a",
                    "title_selector": "h1",
                    "content_selector": "article",
                    "limit": 4,
                    "fulltext_concurrency": 2,
                    "request_delay_seconds": 0.01,
                },
            )
            articles = await scraper.scrape_source(source)
            self.assertEqual(len(articles), 4)
            return scraper

        scraper = asyncio.run(run_case())

        self.assertGreaterEqual(scraper.max_active, 2)
        self.assertLessEqual(scraper.max_active, 2)
        self.assert_domain_spaced(scraper.starts)

    def assert_domain_spaced(self, starts: list[float]) -> None:
        """Assert same-domain request starts are separated by the configured test delay."""
        self.assertEqual(len(starts), 4)
        gaps = [right - left for left, right in zip(starts, starts[1:])]
        self.assertTrue(all(gap >= 0.008 for gap in gaps), gaps)


class FakeResponse:
    """Minimal httpx response replacement for feed fetches."""

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


class RecordingRSSCollector(RSSBase):
    """RSS collector that records concurrent full-text fetches."""

    FULLTEXT_CONCURRENCY = 2
    PER_DOMAIN_DELAY = 0.01

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.starts: list[float] = []

    async def fetch_full_content(self, url: str) -> str:
        loop = asyncio.get_running_loop()
        self.starts.append(loop.time())
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.02)
            return "Full body " * 30
        finally:
            self.active -= 1


class RecordingWebScraper(WebScraperBase):
    """Web scraper that records concurrent article page fetches."""

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.starts: list[float] = []

    async def _allowed(self, url: str) -> bool:
        return True

    async def _fetch_page(self, url: str, *, requires_js: bool = False) -> str:
        if url.endswith("/list"):
            return "".join(f'<a href="/article-{index}">Article {index}</a>' for index in range(4))
        loop = asyncio.get_running_loop()
        self.starts.append(loop.time())
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.02)
            return f"<html><h1>{url}</h1><article>Full article body for {url}</article></html>"
        finally:
            self.active -= 1


if __name__ == "__main__":
    unittest.main()
