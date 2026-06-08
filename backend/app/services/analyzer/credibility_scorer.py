"""Composite media-source credibility scoring."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from redis.asyncio import Redis

from app.config import settings
from app.models.source import Source


class CredibilityScorer:
    """Compute source credibility from MBFC, RSF, transparency, and track record."""

    WEIGHTS = {
        "mbfc_factual": 0.30,
        "rsf_press_freedom": 0.20,
        "transparency": 0.25,
        "track_record": 0.25,
    }

    FACTUAL_SCORES = {
        "very_high": 95,
        "high": 85,
        "mostly_factual": 72,
        "mixed": 55,
        "low": 30,
        "very_low": 10,
    }

    async def fetch_mbfc_score(self, source_name: str) -> dict:
        """Fetch MBFC data through RapidAPI when configured, otherwise return neutral defaults."""
        cache_key = f"mbfc:{source_name.lower()}"
        cached = await self._cache_get(cache_key)
        if cached:
            return cached
        if not settings.mbfc_rapidapi_key:
            result = {"bias": "unknown", "factual": "mixed", "score": 60, "source": source_name}
            await self._cache_set(cache_key, result)
            return result

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.get(
                    "https://media-bias-fact-check.p.rapidapi.com/search",
                    params={"name": source_name},
                    headers={
                        "X-RapidAPI-Key": settings.mbfc_rapidapi_key,
                        "X-RapidAPI-Host": "media-bias-fact-check.p.rapidapi.com",
                    },
                )
                response.raise_for_status()
            payload = response.json()
            record = payload[0] if isinstance(payload, list) and payload else payload
            factual = self._normalize_factual(record.get("factual_reporting") or record.get("factual") or "mixed")
            result = {
                "bias": self._normalize_bias(record.get("bias") or record.get("bias_rating") or "unknown"),
                "factual": factual,
                "score": self.FACTUAL_SCORES.get(factual, 60),
                "source": source_name,
            }
        except Exception:
            result = {"bias": "unknown", "factual": "mixed", "score": 60, "source": source_name}
        await self._cache_set(cache_key, result)
        return result

    async def calculate_transparency(self, source: Source) -> int:
        score = 0
        score += 25 if source.ownership_info else 0
        score += 25 if source.has_correction_policy else 0
        score += 25 if source.separates_news_opinion else 0
        score += 25 if source.funding_info else 0
        return score

    async def compute_composite_score(self, source: Source) -> int:
        transparency = await self.calculate_transparency(source)
        if source.mbfc_score is None:
            mbfc = await self.fetch_mbfc_score(source.name_en or source.name)
            source.mbfc_bias = mbfc.get("bias")
            source.mbfc_factual = mbfc.get("factual")
            source.mbfc_score = int(mbfc.get("score", 60))
        mbfc_score = source.mbfc_score or 60
        rsf_score = self.rsf_country_score(source.country, source.rsf_country_rank)
        track_record = 70
        return round(
            mbfc_score * self.WEIGHTS["mbfc_factual"]
            + rsf_score * self.WEIGHTS["rsf_press_freedom"]
            + transparency * self.WEIGHTS["transparency"]
            + track_record * self.WEIGHTS["track_record"]
        )

    def rsf_country_score(self, country: str, rank: int | None = None) -> int:
        """Return an approximate press-freedom score from seed data or a rank fallback."""
        if rank is not None:
            return max(0, 100 - min(rank, 100))
        data = self._load_rsf_index()
        return int(data.get(country, 50))

    async def update_source_scores(self, source: Source) -> Source:
        """Refresh all credibility fields for one source."""
        mbfc = await self.fetch_mbfc_score(source.name_en or source.name)
        source.mbfc_bias = mbfc.get("bias")
        source.mbfc_factual = mbfc.get("factual")
        source.mbfc_score = int(mbfc.get("score", 60))
        source.transparency_score = await self.calculate_transparency(source)
        source.composite_credibility = await self.compute_composite_score(source)
        return source

    async def _cache_get(self, key: str) -> dict | None:
        try:
            client = Redis.from_url(settings.redis_url, decode_responses=True)
            raw = await client.get(key)
            await client.aclose()
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def _cache_set(self, key: str, value: dict) -> None:
        try:
            client = Redis.from_url(settings.redis_url, decode_responses=True)
            await client.setex(key, 30 * 24 * 60 * 60, json.dumps(value))
            await client.aclose()
        except Exception:
            return

    def _load_rsf_index(self) -> dict[str, int]:
        for parent in Path(__file__).resolve().parents:
            candidate = parent / "data" / "seed" / "rsf_index.json"
            if candidate.exists():
                return json.loads(candidate.read_text(encoding="utf-8"))
        return {}

    @staticmethod
    def _normalize_factual(value: str) -> str:
        normalized = value.lower().replace(" ", "_").replace("-", "_")
        if "very" in normalized and "high" in normalized:
            return "very_high"
        if "mostly" in normalized:
            return "mostly_factual"
        if "high" in normalized:
            return "high"
        if "very" in normalized and "low" in normalized:
            return "very_low"
        if "low" in normalized:
            return "low"
        return "mixed"

    @staticmethod
    def _normalize_bias(value: str) -> str:
        return value.lower().replace(" ", "_").replace("-", "_")
