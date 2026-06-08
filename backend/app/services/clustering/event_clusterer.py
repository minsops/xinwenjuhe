"""Incremental semantic event clustering."""

from __future__ import annotations

import math
from uuid import UUID

from app.config import settings
from app.models.article import Article
from app.services.clustering.embedder import TextEmbedder


class EventClusterer:
    """Assign articles to events by vector similarity and source diversity."""

    def __init__(self, embedder: TextEmbedder | None = None) -> None:
        self.embedder = embedder or TextEmbedder()

    async def embed_article(self, article: Article) -> list[float]:
        text = f"{article.title_original}\n{article.content_translated or article.content_original[:2000]}"
        article.embedding = await self.embedder.embed_text(text[:4096])
        return article.embedding

    async def cluster_new_articles(self, articles: list[Article]) -> dict[int, list[Article]]:
        """Group new articles by embedding similarity without merging unrelated roots."""
        clusters: dict[int, list[Article]] = {}
        for article in articles:
            if not article.embedding:
                await self.embed_article(article)
            assigned = False
            for key, grouped in clusters.items():
                if grouped and self.cosine(article.embedding or [], grouped[0].embedding or []) > settings.cluster_similarity_threshold:
                    clusters[key].append(article)
                    assigned = True
                    break
            if not assigned:
                clusters[len(clusters)] = [article]
        return clusters

    async def merge_events(self, event_a: UUID, event_b: UUID) -> dict:
        """Return merge intent for API/workflow callers to execute transactionally."""
        return {"merge_from": str(event_b), "merge_into": str(event_a), "status": "pending_transaction"}

    @staticmethod
    def cosine(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        denom = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
        return numerator / denom if denom else 0.0
