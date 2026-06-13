"""Tests for event-specific Google News collection orchestration."""

from __future__ import annotations

import asyncio
from importlib.util import find_spec
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import uuid

if not find_spec("feedparser") or not find_spec("sqlalchemy"):
    raise unittest.SkipTest("collector dependencies are not installed")

from app.schemas.article import RawArticle
from app.services.collector.google_news import GoogleNewsCollector
from app.services.collector.ingestion import ArticleIngestionService


class GoogleNewsIngestionTest(unittest.TestCase):
    """Cover Google News event collection without external network or database."""

    def test_event_searches_languages_concurrently_and_keeps_partial_results(self) -> None:
        async def run_case() -> tuple[dict, int]:
            service = ArticleIngestionService(SimpleNamespace(commit=_noop))
            fake = FakeGoogleNews()
            service.google_news = fake
            service.persist_discovered_sources = _persist_discovered_sources
            service._source_for_url = _source_for_url
            service.persist_articles = _persist_articles
            service.refresh_event_stats = _refresh_event_stats
            event = SimpleNamespace(id=uuid.uuid4(), title="test event", title_en="test event")

            with patch.object(GoogleNewsCollector, "REGION_FEEDS", {"en": "feed-en", "fr": "feed-fr", "bad": "feed-bad"}):
                result = await service.collect_google_news_for_event(event)
            return result, fake.max_active

        result, max_active = asyncio.run(run_case())

        self.assertGreaterEqual(max_active, 2)
        self.assertEqual(result["collected"], 2)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual([item["status"] for item in result["languages"]], ["ok", "ok", "failed"])


class FakeGoogleNews:
    """Fake collector that records concurrent search activity."""

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0

    async def search_event(self, query: str, language: str) -> list[RawArticle]:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.01)
            if language == "bad":
                raise RuntimeError("feed failed")
            return [
                RawArticle(
                    external_url=f"https://example.test/{language}",
                    title_original=f"{query} {language}",
                    content_original="Full article body " * 20,
                    language=language,
                )
            ]
        finally:
            self.active -= 1


async def _noop() -> None:
    return None


async def _persist_discovered_sources(raw_articles: list[RawArticle]) -> int:
    return len(raw_articles)


async def _source_for_url(url: str, language: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"{language}:{url}")


async def _persist_articles(raw_articles: list[RawArticle], event_id: uuid.UUID | None = None) -> dict:
    return {"collected": len(raw_articles), "skipped": 0}


async def _refresh_event_stats(event_id: uuid.UUID) -> None:
    return None


if __name__ == "__main__":
    unittest.main()
