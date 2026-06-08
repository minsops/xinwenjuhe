"""Event analysis ORM model containing consensus, disputes, and blind spots."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class EventAnalysis(Base):
    """AI-generated event analysis prepared for the right-side frontend panel."""

    __tablename__ = "event_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), unique=True, nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    consensus_facts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    disputed_facts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    blind_spots: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    narrative_frames: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    source_graph: Mapped[dict | None] = mapped_column(JSONB)
    timeline: Mapped[list[dict] | None] = mapped_column(JSONB)
    analysis_version: Mapped[int] = mapped_column(Integer, default=1)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    article_count_at_analysis: Mapped[int | None] = mapped_column(Integer)

    event = relationship("Event", back_populates="analysis")

