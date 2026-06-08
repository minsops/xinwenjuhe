"""Analysis, fact fragment, and contradiction schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FactFragmentRead(BaseModel):
    """Structured fact fragment returned by analysis APIs."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    article_id: UUID
    source_id: UUID
    fragment_type: str
    content: str
    content_en: str | None = None
    entities: dict | None = None
    numbers: dict | None = None
    source_attribution: str | None = None
    certainty_level: str | None = None
    timestamp_mentioned: datetime | None = None
    created_at: datetime


class ContradictionRead(BaseModel):
    """Contradiction returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    contradiction_type: str
    description: str
    severity: str
    fragment_ids: list[UUID]
    source_ids: list[UUID]
    details: dict | None = None
    created_at: datetime


class EventAnalysisRead(BaseModel):
    """Right-panel event analysis output."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    summary: str
    consensus_facts: list[dict]
    disputed_facts: list[dict]
    blind_spots: list[dict]
    narrative_frames: list[dict]
    source_graph: dict | None = None
    timeline: list[dict] | None = None
    analysis_version: int
    analyzed_at: datetime
    article_count_at_analysis: int | None = None

