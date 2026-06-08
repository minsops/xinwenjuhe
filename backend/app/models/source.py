"""Media source ORM model with feed, transparency, and credibility metadata."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Source(Base):
    """A media organization or feed that can produce articles."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    feed_type: Mapped[str] = mapped_column(String(20), nullable=False)
    feed_url: Mapped[str | None] = mapped_column(Text)
    scraper_config: Mapped[dict | None] = mapped_column(JSONB)
    mbfc_bias: Mapped[str | None] = mapped_column(String(30))
    mbfc_factual: Mapped[str | None] = mapped_column(String(30))
    mbfc_score: Mapped[int | None] = mapped_column(SmallInteger)
    rsf_country_rank: Mapped[int | None] = mapped_column(SmallInteger)
    transparency_score: Mapped[int | None] = mapped_column(SmallInteger)
    composite_credibility: Mapped[int | None] = mapped_column(SmallInteger)
    ownership_info: Mapped[str | None] = mapped_column(Text)
    funding_info: Mapped[str | None] = mapped_column(Text)
    has_correction_policy: Mapped[bool] = mapped_column(Boolean, default=False)
    separates_news_opinion: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    articles = relationship("Article", back_populates="source")

