"""Tests for active source collection orchestration."""

from __future__ import annotations

import asyncio
from importlib.util import find_spec
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import uuid

if not find_spec("sqlalchemy"):
    raise unittest.SkipTest("SQLAlchemy is required for ingestion tests")

from app.config import settings
from app.schemas.article import RawArticle
from app.services.collector.ingestion import ArticleIngestionService


class ActiveSourceIngestionTest(unittest.TestCase):
    """Cover source-level concurrency and failure isolation without network or DB."""

    def test_collect_active_sources_limits_concurrency_and_keeps_partial_results(self) -> None:
        async def run_case() -> tuple[dict, FakeFetcher, list[SimpleNamespace]]:
            sources = [
                _source("good-1"),
                _source("good-2"),
                _source("bad"),
                _source("good-3"),
            ]
            service = ArticleIngestionService(FakeDB(sources))
            fetcher = FakeFetcher()
            service._fetch_source_articles = fetcher.fetch
            service.persist_articles = _persist_articles

            with patch.object(settings, "max_concurrent_scrapers", 2):
                result = await service.collect_active_sources()
            return result, fetcher, sources

        result, fetcher, sources = asyncio.run(run_case())
        statuses = [item["status"] for item in result["results"]]

        self.assertEqual(result["sources"], 4)
        self.assertEqual(result["collected"], 3)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(statuses, ["ok", "ok", "failed", "ok"])
        self.assertGreaterEqual(fetcher.max_active, 2)
        self.assertLessEqual(fetcher.max_active, 2)
        self.assertEqual(sources[2].consecutive_failures, 1)
        successful_sources = (sources[0], sources[1], sources[3])
        self.assertTrue(all(source.last_collected_at for source in successful_sources))


class FakeResult:
    """Minimal result object for AsyncSession.execute."""

    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self.rows = rows

    def scalars(self) -> "FakeResult":
        return self

    def all(self) -> list[SimpleNamespace]:
        return self.rows


class FakeDB:
    """Async session double that returns configured sources."""

    def __init__(self, sources: list[SimpleNamespace]) -> None:
        self.sources = sources
        self.commits = 0

    async def execute(self, query) -> FakeResult:
        return FakeResult(self.sources)

    async def commit(self) -> None:
        self.commits += 1


class FakeFetcher:
    """Fetch helper that records concurrent network work."""

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0

    async def fetch(self, source: SimpleNamespace) -> list[RawArticle]:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.01)
            if source.name == "bad":
                raise RuntimeError("source failed")
            return [
                RawArticle(
                    external_url=f"https://example.test/{source.name}",
                    title_original=source.name,
                    content_original="Full body",
                    language=source.language,
                )
            ]
        finally:
            self.active -= 1


def _source(name: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        is_active=True,
        last_collected_at=None,
        consecutive_failures=0,
        language="en",
    )


async def _persist_articles(
    raw_articles: list[RawArticle],
    fallback_source: SimpleNamespace | None = None,
    event_id: uuid.UUID | None = None,
) -> dict:
    return {"collected": len(raw_articles), "skipped": 0}


if __name__ == "__main__":
    unittest.main()
