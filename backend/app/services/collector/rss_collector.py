"""RSS and Atom feed collection with full-text extraction."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from uuid import UUID

import feedparser
import httpx
import trafilatura
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.source import Source
from app.schemas.article import RawArticle
from app.services.collector.rate_limiter import DomainRateLimiter


class RSSCollector:
    """Collect articles from RSS 2.0 and Atom feeds."""

    FULLTEXT_CONCURRENCY = 5
    PER_DOMAIN_DELAY = 0.5
    USER_AGENTS = [
        "TruthPuzzle/0.1 (+https://truthpuzzle.local)",
        "Mozilla/5.0 (compatible; TruthPuzzleBot/0.1; +https://truthpuzzle.local)",
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def fetch_feed(self, source: Source) -> list[RawArticle]:
        if not source.feed_url:
            return []
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(source.feed_url, headers={"User-Agent": random.choice(self.USER_AGENTS)})
            response.raise_for_status()
        parsed = feedparser.parse(response.content)
        semaphore = asyncio.Semaphore(self.FULLTEXT_CONCURRENCY)
        domain_limiter = DomainRateLimiter(self.PER_DOMAIN_DELAY)

        async def parse_entry(entry) -> RawArticle | None:
            published_at = self._parse_date(
                getattr(entry, "published", None) or getattr(entry, "updated", None)
            )
            if source.last_collected_at and published_at and published_at <= source.last_collected_at:
                return None
            link = getattr(entry, "link", "")
            if not link:
                return None
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            async with semaphore:
                await domain_limiter.wait(link)
                try:
                    content = await self.fetch_full_content(link)
                except Exception:
                    content = ""
                content = content or trafilatura.extract(summary) or summary
            return RawArticle(
                source_id=source.id,
                external_url=link,
                title_original=getattr(entry, "title", "Untitled"),
                content_original=content or "",
                language=source.language,
                published_at=published_at,
                author=getattr(entry, "author", None),
                metadata={"feed_id": getattr(entry, "id", None)},
            )
        rows = await asyncio.gather(*(parse_entry(entry) for entry in parsed.entries))
        articles = [row for row in rows if row is not None]
        return articles

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    async def fetch_full_content(self, url: str) -> str:
        """Fetch and extract article body text with trafilatura."""
        downloaded = await asyncio.to_thread(trafilatura.fetch_url, url)
        if not downloaded:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": random.choice(self.USER_AGENTS)})
                response.raise_for_status()
                downloaded = response.text
        return (
            trafilatura.extract(
                downloaded,
                url=url,
                include_comments=False,
                include_tables=False,
                favor_recall=True,
            )
            or ""
        )

    @staticmethod
    def _parse_date(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            parsed = parsedate_to_datetime(raw)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None
