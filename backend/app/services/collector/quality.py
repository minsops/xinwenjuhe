"""Collection quality metrics for source health monitoring."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.config import settings
from app.models.source import Source
from app.schemas.article import RawArticle


COLLECTION_METRICS_HISTORY_KEY = "collection_metrics_history"


@dataclass(slots=True)
class CollectionMetrics:
    """Quality metrics for one source collection run."""

    source_id: str
    source_name: str
    feed_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    articles_fetched: int = 0
    articles_with_fulltext: int = 0
    articles_empty_content: int = 0
    articles_short_content: int = 0
    articles_deduplicated: int = 0
    fulltext_fetch_errors: int = 0
    avg_content_length: float = 0.0
    avg_fetch_latency_ms: float = 0.0

    @property
    def fulltext_success_rate(self) -> float:
        if self.articles_fetched == 0:
            return 0.0
        return self.articles_with_fulltext / self.articles_fetched

    @property
    def empty_content_rate(self) -> float:
        if self.articles_fetched == 0:
            return 0.0
        return self.articles_empty_content / self.articles_fetched

    @property
    def is_healthy(self) -> bool:
        return self.articles_fetched > 0 and self.fulltext_success_rate > 0.5

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "feed_type": self.feed_type,
            "timestamp": self.timestamp.isoformat(),
            "articles_fetched": self.articles_fetched,
            "articles_with_fulltext": self.articles_with_fulltext,
            "articles_empty_content": self.articles_empty_content,
            "articles_short_content": self.articles_short_content,
            "articles_deduplicated": self.articles_deduplicated,
            "fulltext_fetch_errors": self.fulltext_fetch_errors,
            "fulltext_success_rate": round(self.fulltext_success_rate, 3),
            "empty_content_rate": round(self.empty_content_rate, 3),
            "avg_content_length": round(self.avg_content_length, 1),
            "avg_fetch_latency_ms": round(self.avg_fetch_latency_ms, 1),
            "is_healthy": self.is_healthy,
        }


def build_collection_metrics(
    source: Source,
    raw_articles: list[RawArticle],
    result: dict | None = None,
    fulltext_fetch_errors: int = 0,
) -> CollectionMetrics:
    """Build source quality metrics from fetched articles and persistence result."""
    lengths = [len(article.content_original or "") for article in raw_articles]
    result = result or {}
    return CollectionMetrics(
        source_id=str(source.id),
        source_name=getattr(source, "name", str(source.id)),
        feed_type=getattr(source, "feed_type", "unknown"),
        articles_fetched=len(raw_articles),
        articles_with_fulltext=sum(1 for length in lengths if length >= 200),
        articles_empty_content=sum(1 for length in lengths if length == 0),
        articles_short_content=sum(1 for length in lengths if 0 < length < 200),
        articles_deduplicated=int(result.get("skipped", 0) or 0),
        fulltext_fetch_errors=fulltext_fetch_errors,
        avg_content_length=sum(lengths) / max(len(lengths), 1),
    )


async def record_collection_metrics(metrics: CollectionMetrics) -> None:
    """Persist collection metrics in Redis for operator dashboards."""
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        payload = json.dumps(metrics.to_dict(), ensure_ascii=False)
        await client.setex(f"collection_metrics:{metrics.source_id}", 24 * 60 * 60, payload)
        await client.lpush(COLLECTION_METRICS_HISTORY_KEY, payload)
        await client.ltrim(COLLECTION_METRICS_HISTORY_KEY, 0, 499)
        await client.aclose()
    except Exception:
        return


async def list_collection_metrics(limit: int = 50) -> list[dict]:
    """Return recent collection metrics from Redis."""
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        rows = await client.lrange(COLLECTION_METRICS_HISTORY_KEY, 0, max(limit - 1, 0))
        await client.aclose()
        return [json.loads(row) for row in rows]
    except Exception:
        return []
