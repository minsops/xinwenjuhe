"""Article API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.source import SourceRead


class RawArticle(BaseModel):
    """Collector DTO before persistence."""

    source_id: UUID | None = None
    external_url: str
    title_original: str
    content_original: str
    language: str
    published_at: datetime | None = None
    author: str | None = None
    image_url: str | None = None
    metadata: dict | None = None


class ArticleRead(BaseModel):
    """Article returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    external_url: str
    title_original: str
    title_translated: str | None = None
    content_original: str
    content_translated: str | None = None
    language: str
    published_at: datetime | None = None
    collected_at: datetime
    author: str | None = None
    image_url: str | None = None
    event_id: UUID | None = None
    article_metadata: dict | None = None
    created_at: datetime
    source: SourceRead | None = None


class TranslateRequest(BaseModel):
    """Translation request body."""

    target_lang: str = "zh"


class TranslateResponse(BaseModel):
    """One-click article translation response."""

    title: str
    content: str
    cached: bool

