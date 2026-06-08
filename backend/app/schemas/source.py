"""Source API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SourceBase(BaseModel):
    name: str
    name_en: str | None = None
    country: str
    region: str
    language: str
    feed_type: str
    feed_url: str | None = None
    scraper_config: dict | None = None
    ownership_info: str | None = None
    funding_info: str | None = None
    has_correction_policy: bool = False
    separates_news_opinion: bool = False


class SourceCreate(SourceBase):
    """Payload used to create or seed a source."""


class SourceRead(SourceBase):
    """Source returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    mbfc_bias: str | None = None
    mbfc_factual: str | None = None
    mbfc_score: int | None = None
    rsf_country_rank: int | None = None
    transparency_score: int | None = None
    composite_credibility: int | None = None
    is_active: bool
    last_collected_at: datetime | None = None
    scraper_verified_at: datetime | None = None
    consecutive_failures: int = 0
    created_at: datetime
    updated_at: datetime
