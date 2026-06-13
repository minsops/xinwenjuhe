"""Trending topic discovery for automatic event seeding."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.article import Article


@dataclass(slots=True)
class TrendingTopic:
    """A discovered topic and enough context to collect related reporting."""

    title: str
    keywords: list[str]
    source: str
    language: str = "en"
    region_hint: str | None = None
    url: str | None = None
    score: float = 0.0


class TrendingProvider(Protocol):
    """Provider interface for new trending signals."""

    async def fetch_trending(self) -> list[TrendingTopic]:
        """Return currently trending topics."""


class TrendingDiscovery:
    """Aggregate multiple trending signals and deduplicate them."""

    def __init__(self, providers: list[TrendingProvider] | None = None) -> None:
        if providers is None:
            providers = [
                GoogleTrendsProvider(),
                GDELTProvider(),
                CrossSourceTitleProvider(),
            ]
        self.providers = providers

    def register_provider(self, provider: TrendingProvider) -> None:
        """Register a new provider without changing discovery orchestration."""
        self.providers.append(provider)

    async def discover(self, limit: int = 20) -> list[TrendingTopic]:
        """Fetch, merge, and rank trending topics from all providers."""
        topics: list[TrendingTopic] = []
        for provider in self.providers:
            try:
                topics.extend(await provider.fetch_trending())
            except Exception:
                continue
        return self.deduplicate(topics)[:limit]

    @staticmethod
    def deduplicate(topics: list[TrendingTopic]) -> list[TrendingTopic]:
        """Merge topics whose keyword overlap indicates the same story."""
        groups: list[TrendingTopic] = []
        for topic in topics:
            tokens = set(_topic_tokens(topic))
            if not tokens:
                continue
            for existing in groups:
                existing_tokens = set(_topic_tokens(existing))
                if not existing_tokens:
                    continue
                overlap = len(tokens & existing_tokens) / min(len(tokens), len(existing_tokens))
                if overlap > 0.6:
                    existing.score = max(existing.score, topic.score)
                    existing.keywords = sorted(set(existing.keywords) | set(topic.keywords))
                    if topic.source not in existing.source.split("+"):
                        existing.source = f"{existing.source}+{topic.source}"
                    break
            else:
                groups.append(topic)
        return sorted(groups, key=lambda item: item.score, reverse=True)


class GoogleTrendsProvider:
    """Fetch region-specific Google Trends RSS feeds."""

    TREND_FEEDS: dict[str, str] = {
        "US": "https://trends.google.com/trending/rss?geo=US",
        "GB": "https://trends.google.com/trending/rss?geo=GB",
        "DE": "https://trends.google.com/trending/rss?geo=DE",
        "FR": "https://trends.google.com/trending/rss?geo=FR",
        "JP": "https://trends.google.com/trending/rss?geo=JP",
        "KR": "https://trends.google.com/trending/rss?geo=KR",
        "IN": "https://trends.google.com/trending/rss?geo=IN",
        "BR": "https://trends.google.com/trending/rss?geo=BR",
        "RU": "https://trends.google.com/trending/rss?geo=RU",
        "SA": "https://trends.google.com/trending/rss?geo=SA",
        "EG": "https://trends.google.com/trending/rss?geo=EG",
        "NG": "https://trends.google.com/trending/rss?geo=NG",
        "ZA": "https://trends.google.com/trending/rss?geo=ZA",
        "TR": "https://trends.google.com/trending/rss?geo=TR",
        "MX": "https://trends.google.com/trending/rss?geo=MX",
        "AR": "https://trends.google.com/trending/rss?geo=AR",
        "AU": "https://trends.google.com/trending/rss?geo=AU",
        "IL": "https://trends.google.com/trending/rss?geo=IL",
        "PK": "https://trends.google.com/trending/rss?geo=PK",
        "TW": "https://trends.google.com/trending/rss?geo=TW",
    }
    COUNTRY_TO_REGION: dict[str, str] = {
        "US": "north_america",
        "GB": "europe",
        "DE": "europe",
        "FR": "europe",
        "JP": "east_asia",
        "KR": "east_asia",
        "IN": "south_asia",
        "BR": "latin_america",
        "RU": "russia_cis",
        "SA": "middle_east",
        "EG": "middle_east",
        "NG": "africa",
        "ZA": "africa",
        "TR": "middle_east",
        "MX": "latin_america",
        "AR": "latin_america",
        "AU": "north_america",
        "IL": "middle_east",
        "PK": "south_asia",
        "TW": "east_asia",
    }

    async def fetch_trending(self) -> list[TrendingTopic]:
        """Return top Google Trends entries from configured regions."""
        topics: list[TrendingTopic] = []
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            for country, url in self.TREND_FEEDS.items():
                try:
                    response = await client.get(url, headers={"User-Agent": "TruthPuzzle/0.1"})
                    if response.status_code != 200:
                        continue
                    parsed = feedparser.parse(response.content)
                    for entry in parsed.entries[:5]:
                        title = getattr(entry, "title", "").strip()
                        if not title:
                            continue
                        traffic = self.parse_traffic(getattr(entry, "ht_approx_traffic", "0"))
                        topics.append(
                            TrendingTopic(
                                title=title,
                                keywords=extract_keywords(title),
                                source="google_trends",
                                region_hint=self.COUNTRY_TO_REGION.get(country),
                                url=getattr(entry, "link", None),
                                score=min(100.0, traffic / 10000),
                            )
                        )
                except Exception:
                    continue
        return topics

    @staticmethod
    def parse_traffic(value: str) -> float:
        """Parse Google Trends traffic strings such as '20,000+'."""
        cleaned = re.sub(r"[^\d]", "", value)
        return float(cleaned) if cleaned else 0.0


class GDELTProvider:
    """Fetch globally relevant article topics from the GDELT DOC API."""

    GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"

    async def fetch_trending(self) -> list[TrendingTopic]:
        """Return GDELT article titles as topic seeds."""
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.get(
                    self.GDELT_API,
                    params={
                        "query": "sourcelang:english",
                        "mode": "ArtList",
                        "timespan": "24h",
                        "maxrecords": "30",
                        "format": "json",
                        "sort": "HybridRel",
                    },
                    headers={"User-Agent": "TruthPuzzle/0.1"},
                )
                if response.status_code != 200:
                    return []
                data = response.json()
        except Exception:
            return []

        topics: list[TrendingTopic] = []
        for item in (data.get("articles") if isinstance(data, dict) else data) or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            topics.append(
                TrendingTopic(
                    title=title,
                    keywords=extract_keywords(title),
                    source="gdelt",
                    url=item.get("url"),
                    score=50.0,
                )
            )
        return topics


class CrossSourceTitleProvider:
    """Mine recent collected titles for terms repeated across independent sources."""

    async def fetch_trending(self) -> list[TrendingTopic]:
        """No implicit DB session is available in generic discovery."""
        return []

    async def fetch_from_db(self, db: AsyncSession, limit: int = 10) -> list[TrendingTopic]:
        """Return terms appearing in recent titles from at least three sources."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
        rows = (
            await db.execute(
                select(Article.title_original, Article.source_id).where(Article.created_at >= cutoff)
            )
        ).all()
        source_map: dict[str, set] = {}
        for title, source_id in rows:
            for token in extract_keywords(title):
                source_map.setdefault(token.lower(), set()).add(source_id)
        ranked = Counter({token: len(sources) for token, sources in source_map.items() if len(sources) >= 3})
        return [
            TrendingTopic(
                title=token,
                keywords=[token],
                source="cross_source_title",
                score=min(100.0, count * 10.0),
            )
            for token, count in ranked.most_common(limit)
        ]


def extract_keywords(title: str) -> list[str]:
    """Extract non-stopword keyword tokens from a topic title."""
    keywords: list[str] = []
    for word in re.split(r"[\s,\-–—/()：:;，。！？!?]+", title):
        token = word.strip(".,'\"“”‘’[]{}").lower()
        if len(token) < 2 or token in STOP_WORDS:
            continue
        keywords.append(token)
    return keywords


def _topic_tokens(topic: TrendingTopic) -> list[str]:
    return topic.keywords or extract_keywords(topic.title)


STOP_WORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "for",
    "and",
    "nor",
    "but",
    "or",
    "yet",
    "so",
    "in",
    "on",
    "at",
    "to",
    "from",
    "by",
    "with",
    "about",
    "into",
    "through",
    "that",
    "this",
    "these",
    "those",
    "not",
    "its",
    "his",
    "her",
    "their",
    "our",
    "your",
    "more",
    "most",
    "other",
    "some",
    "any",
    "all",
    "each",
    "new",
    "old",
    "said",
    "says",
    "after",
    "before",
    "over",
    "under",
    "between",
    "than",
    "also",
    "just",
    "only",
    "very",
    "how",
    "what",
    "when",
    "where",
    "who",
    "which",
    "why",
    "news",
    "report",
    "reports",
    "update",
    "latest",
}
