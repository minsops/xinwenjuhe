"""Tests for historical archive backfill services."""

from __future__ import annotations

import asyncio
import importlib.util
import unittest
from datetime import datetime, timezone

if not importlib.util.find_spec("httpx") or not importlib.util.find_spec("sqlalchemy"):
    raise unittest.SkipTest("archive collector dependencies are required")

from app.schemas.article import RawArticle
from app.services.collector.archive import ArchiveQuery, ArchiveService, GDELTArchiveProvider


class ArchiveServiceTest(unittest.TestCase):
    """Validate archive provider mapping and full-text enrichment."""

    def test_gdelt_provider_maps_articles(self) -> None:
        rows = GDELTArchiveProvider._parse_articles(
            {
                "articles": [
                    {
                        "url": "https://example.test/story",
                        "title": "Port strike disrupts shipments",
                        "language": "English",
                        "seendate": "20260613091500",
                        "domain": "example.test",
                        "sourcecountry": "US",
                        "tone": "-1.2",
                    },
                    {"url": "", "title": "missing url"},
                ]
            }
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].external_url, "https://example.test/story")
        self.assertEqual(rows[0].content_original, "Port strike disrupts shipments")
        self.assertEqual(rows[0].metadata["archive"], "gdelt")
        self.assertEqual(rows[0].published_at, datetime(2026, 6, 13, 9, 15, tzinfo=timezone.utc))

    def test_archive_service_registers_provider_and_deduplicates(self) -> None:
        query = _query()
        service = ArchiveService(providers=[FakeProvider("one")])
        service.register_provider(FakeProvider("two"))

        articles = asyncio.run(service.backfill(query))

        self.assertEqual([article.external_url for article in articles], ["https://example.test/a"])

    def test_backfill_with_fulltext_enriches_short_archive_records(self) -> None:
        service = ArchiveService(providers=[FakeProvider("one")], fetcher_factory=FakeFetcher)

        articles = asyncio.run(service.backfill_with_fulltext(_query(), fetch_content=True))

        self.assertEqual(len(articles), 1)
        self.assertGreater(len(articles[0].content_original), 200)
        self.assertIn("full archived article", articles[0].content_original)


class FakeProvider:
    """Archive provider test double."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def health_check(self) -> bool:
        return True

    async def search(self, query: ArchiveQuery) -> list[RawArticle]:
        return [
            RawArticle(
                external_url="https://example.test/a",
                title_original=f"story from {self.name}",
                content_original="short",
                language="en",
                metadata={"archive": self.name},
            )
        ]


class FakeFetcher:
    """Full-text fetcher test double."""

    async def fetch_full_content(self, url: str) -> str:
        return "full archived article " * 20


def _query() -> ArchiveQuery:
    return ArchiveQuery(
        keywords=["port", "strike"],
        date_from=datetime(2026, 6, 1, tzinfo=timezone.utc),
        date_to=datetime(2026, 6, 13, tzinfo=timezone.utc),
        max_results=10,
    )


if __name__ == "__main__":
    unittest.main()
