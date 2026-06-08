"""Discovered source API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DiscoveredSourceCreate(BaseModel):
    """Community or operator-submitted source candidate."""

    domain: str
    language: str | None = None
    region_hint: str | None = None
    sample_urls: list[str] | None = None


class DiscoveredSourceRead(BaseModel):
    """Source candidate returned by discovery APIs."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain: str
    language: str | None = None
    region_hint: str | None = None
    status: str
    sample_urls: list[str] | None = None
    created_at: datetime
    updated_at: datetime
