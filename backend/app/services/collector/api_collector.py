"""Generic JSON API news collection for configured source endpoints."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.source import Source
from app.schemas.article import RawArticle


class APICollector:
    """Collect articles from JSON APIs using source.scraper_config field mappings."""

    USER_AGENTS = [
        "TruthPuzzle/0.1 (+https://truthpuzzle.local)",
        "Mozilla/5.0 (compatible; TruthPuzzleBot/0.1; +https://truthpuzzle.local)",
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def fetch_feed(self, source: Source) -> list[RawArticle]:
        """Fetch and map a configured JSON API response into RawArticle records."""
        if not source.feed_url:
            return []
        config = source.scraper_config or {}
        headers = {"User-Agent": random.choice(self.USER_AGENTS)}
        headers.update(config.get("headers") or {})
        params = config.get("params") or {}
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(source.feed_url, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()

        items = self._value(payload, config.get("items_path", "items"))
        if isinstance(items, dict):
            items = list(items.values())
        if not isinstance(items, list):
            return []

        articles: list[RawArticle] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            published_at = self._parse_date(self._value(item, config.get("date_path", "published_at")))
            if source.last_collected_at and published_at and published_at <= source.last_collected_at:
                continue
            url = self._value(item, config.get("url_path", "url"))
            title = self._value(item, config.get("title_path", "title"))
            content = self._value(item, config.get("content_path", "content"))
            if not url or not title or not content:
                continue
            articles.append(
                RawArticle(
                    source_id=source.id,
                    external_url=str(url),
                    title_original=str(title),
                    content_original=str(content),
                    language=source.language,
                    published_at=published_at,
                    author=self._optional_str(self._value(item, config.get("author_path", "author"))),
                    image_url=self._optional_str(self._value(item, config.get("image_path", "image_url"))),
                    metadata={"api": True, "endpoint": source.feed_url},
                )
            )
        return articles

    @classmethod
    def _value(cls, payload: Any, path: str | None) -> Any:
        """Read a simple dot-separated path from dict/list JSON payloads."""
        current = payload
        for part in (path or "").split("."):
            if not part:
                continue
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)] if int(part) < len(current) else None
            else:
                return None
        return current

    @staticmethod
    def _parse_date(raw: Any) -> datetime | None:
        if not raw:
            return None
        value = str(raw)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                return None

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        return str(value) if value else None
