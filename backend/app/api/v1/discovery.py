"""Source discovery review routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, envelope
from app.db import get_db
from app.models.discovered_source import DiscoveredSource
from app.models.source import Source
from app.schemas.discovery import DiscoveredSourceCreate, DiscoveredSourceRead

router = APIRouter()


@router.post("/sources")
async def submit_discovered_source(
    payload: DiscoveredSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Submit a community source candidate for review."""
    domain = payload.domain.removeprefix("https://").removeprefix("http://").strip("/").lower()
    if not domain or "." not in domain:
        raise ApiError("invalid_domain", "Candidate domain is invalid", 422)
    existing = await db.scalar(select(DiscoveredSource).where(DiscoveredSource.domain == domain))
    if existing:
        existing.language = payload.language or existing.language
        existing.region_hint = payload.region_hint or existing.region_hint
        urls = set(existing.sample_urls or [])
        urls.update(payload.sample_urls or [])
        existing.sample_urls = sorted(urls)[:5]
        await db.commit()
        await db.refresh(existing)
        return envelope(DiscoveredSourceRead.model_validate(existing).model_dump(mode="json"))
    candidate = DiscoveredSource(
        domain=domain,
        language=payload.language,
        region_hint=payload.region_hint,
        status="pending_review",
        sample_urls=(payload.sample_urls or [])[:5],
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return envelope(DiscoveredSourceRead.model_validate(candidate).model_dump(mode="json"))


@router.get("/sources")
async def list_discovered_sources(
    db: AsyncSession = Depends(get_db),
    status: str = "pending_review",
    limit: int = Query(50, ge=1, le=200),
):
    rows = (
        await db.execute(
            select(DiscoveredSource)
            .where(DiscoveredSource.status == status)
            .order_by(DiscoveredSource.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return envelope([DiscoveredSourceRead.model_validate(row).model_dump(mode="json") for row in rows], total=len(rows))


@router.post("/sources/{candidate_id}/status")
async def update_discovered_source_status(
    candidate_id: UUID,
    status: str,
    db: AsyncSession = Depends(get_db),
):
    if status not in {"pending_review", "approved", "rejected"}:
        raise ApiError("invalid_status", "Invalid discovery status", 422)
    candidate = await db.get(DiscoveredSource, candidate_id)
    if not candidate:
        raise ApiError("candidate_not_found", "Discovered source candidate not found", 404)
    candidate.status = status
    await db.commit()
    await db.refresh(candidate)
    return envelope(DiscoveredSourceRead.model_validate(candidate).model_dump(mode="json"))


@router.post("/sources/{candidate_id}/approve")
async def approve_discovered_source(
    candidate_id: UUID,
    country: str = "Unknown",
    region: str = "unknown",
    db: AsyncSession = Depends(get_db),
):
    """Approve a discovered candidate and create a formal source record."""
    candidate = await db.get(DiscoveredSource, candidate_id)
    if not candidate:
        raise ApiError("candidate_not_found", "Discovered source candidate not found", 404)
    existing = await db.scalar(select(Source).where(Source.feed_url == f"https://{candidate.domain}"))
    if existing:
        candidate.status = "approved"
        await db.commit()
        return envelope({"source_id": str(existing.id), "candidate_id": str(candidate.id), "status": "approved"})
    source = Source(
        name=candidate.domain,
        name_en=candidate.domain,
        country=country,
        region=region,
        language=candidate.language or "unknown",
        feed_type="google_news",
        feed_url=f"https://{candidate.domain}",
        is_active=False,
        transparency_score=0,
        composite_credibility=45,
    )
    candidate.status = "approved"
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return envelope({"source_id": str(source.id), "candidate_id": str(candidate.id), "status": "approved"})
