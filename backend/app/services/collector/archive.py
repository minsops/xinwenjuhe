"""Historical news archive collectors for event backfill."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

from app.config import settings
from app.schemas.article import RawArticle


@dataclass(slots=True)
class ArchiveQuery:
    """Standard query object shared by archive providers."""

    keywords: list[str]
    date_from: datetime
    date_to: datetime
    languages: list[str] | None = None
    regions: list[str] | None = None
    max_results: int = 100
    source_domains: list[str] | None = None


class ArchiveProvider(Protocol):
    """Interface for historical archive backfill providers."""

    @property
    def name(self) -> str:
        """Provider identifier."""

    async def search(self, query: ArchiveQuery) -> list[RawArticle]:
        """Return historical articles matching the query."""

    async def health_check(self) -> bool:
        """Return whether this provider is currently usable."""


class GDELTArchiveProvider:
    """GDELT DOC 2.0 archive provider."""

    API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

    @property
    def name(self) -> str:
        return "gdelt"

    async def search(self, query: ArchiveQuery) -> list[RawArticle]:
        """Search GDELT and map article list results to RawArticle DTOs."""
        keyword_query = " ".join(query.keywords[:10]).strip()
        if not keyword_query:
            return []
        params: dict[str, Any] = {
            "query": self._query_string(keyword_query, query),
            "mode": "ArtList",
            "maxrecords": str(min(query.max_results, 250)),
            "format": "json",
            "startdatetime": _gdelt_datetime(query.date_from),
            "enddatetime": _gdelt_datetime(query.date_to),
            "sort": "DateDesc",
        }
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(self.API_URL, params=params, headers={"User-Agent": "TruthPuzzle/0.1"})
            if response.status_code != 200:
                return []
            data = response.json()
        return self._parse_articles(data)

    async def health_check(self) -> bool:
        """Check that GDELT responds to a tiny article-list query."""
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.get(
                    self.API_URL,
                    params={"query": "test", "mode": "ArtList", "maxrecords": "1", "format": "json"},
                    headers={"User-Agent": "TruthPuzzle/0.1"},
                )
                return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _query_string(keyword_query: str, query: ArchiveQuery) -> str:
        parts = [f"({keyword_query})"]
        if query.languages:
            languages = " OR ".join(f"sourcelang:{language.split('-')[0].lower()}" for language in query.languages)
            parts.append(f"({languages})")
        if query.source_domains:
            domains = " OR ".join(f"domain:{domain}" for domain in query.source_domains)
            parts.append(f"({domains})")
        return " ".join(parts)

    @classmethod
    def _parse_articles(cls, data: dict | list) -> list[RawArticle]:
        rows = data.get("articles", []) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            return []
        articles: list[RawArticle] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            if not url or not title:
                continue
            articles.append(
                RawArticle(
                    external_url=url,
                    title_original=title,
                    content_original=title,
                    language=str(item.get("language") or "en")[:10],
                    published_at=cls._parse_gdelt_date(item.get("seendate")),
                    author=item.get("sourcecountry"),
                    metadata={
                        "archive": "gdelt",
                        "domain": item.get("domain"),
                        "source_country": item.get("sourcecountry"),
                        "tone": item.get("tone"),
                        "socialimage": item.get("socialimage"),
                    },
                )
            )
        return articles

    @staticmethod
    def _parse_gdelt_date(value: str | None) -> datetime | None:
        if not value:
            return None
        candidates = [
            (value[:14], "%Y%m%d%H%M%S"),
            (value[:16], "%Y%m%dT%H%M%SZ"),
        ]
        for raw, fmt in candidates:
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None


class ArchiveService:
    """Backfill service that aggregates providers and optionally fetches full text."""

    def __init__(self, providers: list[ArchiveProvider] | None = None, fetcher_factory=None) -> None:
        self.providers = providers if providers is not None else [GDELTArchiveProvider()]
        self.fetcher_factory = fetcher_factory

    def register_provider(self, provider: ArchiveProvider) -> None:
        """Register a new archive provider without changing service orchestration."""
        self.providers.append(provider)

    async def backfill(self, query: ArchiveQuery) -> list[RawArticle]:
        """Search providers and deduplicate results by URL."""
        articles: list[RawArticle] = []
        seen_urls: set[str] = set()
        for provider in self.providers:
            try:
                if not await provider.health_check():
                    continue
                for article in await provider.search(query):
                    if article.external_url in seen_urls:
                        continue
                    seen_urls.add(article.external_url)
                    articles.append(article)
                    if len(articles) >= query.max_results:
                        return articles
            except Exception:
                continue
        return articles

    async def backfill_with_fulltext(self, query: ArchiveQuery, fetch_content: bool = True) -> list[RawArticle]:
        """Backfill archive hits and enrich short records with extracted full text."""
        articles = await self.backfill(query)
        if not fetch_content:
            return articles
        fetcher = self._fetcher()
        enriched: list[RawArticle] = []
        for article in articles:
            if len(article.content_original.strip()) >= 200:
                enriched.append(article)
                continue
            try:
                content = await fetcher.fetch_full_content(article.external_url)
            except Exception:
                continue
            if len(content.strip()) < 50:
                continue
            article.content_original = content
            enriched.append(article)
        return enriched

    def _fetcher(self):
        if self.fetcher_factory:
            return self.fetcher_factory()
        from app.services.collector.rss_collector import RSSCollector

        return RSSCollector()


def _gdelt_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
