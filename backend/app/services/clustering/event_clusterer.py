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
            if not _has_vector(article.embedding):
                await self.embed_article(article)
            assigned = False
            for key, grouped in clusters.items():
                if grouped and self.cosine(article.embedding, grouped[0].embedding) > settings.cluster_similarity_threshold:
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
    def cosine(left: list[float] | None, right: list[float] | None) -> float:
        left_values = _vector_values(left)
        right_values = _vector_values(right)
        if not left_values or not right_values or len(left_values) != len(right_values):
            return 0.0
        numerator = sum(a * b for a, b in zip(left_values, right_values, strict=False))
        denom = math.sqrt(sum(a * a for a in left_values)) * math.sqrt(sum(b * b for b in right_values))
        return numerator / denom if denom else 0.0


def _has_vector(vector: list[float] | None) -> bool:
    return vector is not None and len(vector) > 0


def _vector_values(vector: list[float] | None) -> list[float]:
    if vector is None:
        return []
    return list(vector)
