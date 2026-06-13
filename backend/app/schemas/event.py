"""Event API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EventRead(BaseModel):
    """Event returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    title_en: str | None = None
    title_zh: str | None = None
    summary: str | None = None
    summary_zh: str | None = None
    category: str | None = None
    region_primary: str | None = None
    regions_involved: list[str] | None = None
    status: str
    article_count: int
    source_count: int
    language_count: int
    region_count: int
    heat_score: float
    first_reported_at: datetime | None = None
    last_updated_at: datetime | None = None
    created_at: datetime


class EventCreate(BaseModel):
    """Minimal manual event creation payload."""

    title: str
    summary: str | None = None
    category: str | None = None
    region_primary: str | None = None
    regions_involved: list[str] | None = None


class EventMergeRequest(BaseModel):
    """Merge another event into the target event."""

    source_event_id: UUID


class EventSplitRequest(BaseModel):
    """Split selected articles into a new event."""

    article_ids: list[UUID]
    title: str | None = None
