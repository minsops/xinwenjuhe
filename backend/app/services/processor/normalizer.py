"""Article normalization helpers used before persistence and clustering."""

from __future__ import annotations

from app.schemas.article import RawArticle
from app.services.processor.deduplicator import Deduplicator


class ArticleNormalizer:
    """Normalize collected article DTOs into clean text values."""

    def __init__(self) -> None:
        self.deduplicator = Deduplicator()

    def normalize(self, article: RawArticle) -> RawArticle:
        article.content_original = self.deduplicator.normalize_text(article.content_original)
        article.title_original = self.deduplicator.normalize_text(article.title_original)
        return article

