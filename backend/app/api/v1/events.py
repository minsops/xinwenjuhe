"""Event list, detail, related articles, analysis, contradictions, and timeline routes."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ApiError, envelope
from app.db import get_db
from app.models.article import Article
from app.models.contradiction import Contradiction
from app.models.credibility import EventAnalysis
from app.models.event import Event
from app.models.source import Source
from app.schemas.analysis import ContradictionRead, EventAnalysisRead
from app.schemas.article import ArticleRead
from app.schemas.event import EventCreate, EventMergeRequest, EventRead, EventSplitRequest
from app.services.clustering.pipeline import EventClusteringService
from app.services.collector.ingestion import ArticleIngestionService
from app.services.analyzer.event_analysis_service import EventAnalysisService
from app.services.event_management import EventManagementService
from app.api.v1.websocket import notify_event_update
from app.tasks.analyze_task import process_event_pipeline

router = APIRouter()


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_cursor_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ApiError("invalid_cursor", "Cursor is invalid for this endpoint", 400)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApiError("invalid_cursor", "Cursor is invalid for this endpoint", 400) from exc


def _encode_cursor(kind: str, payload: dict) -> str:
    raw = json.dumps({"kind": kind, **payload}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str, expected_kind: str) -> dict:
    try:
        padded = cursor + ("=" * (-len(cursor) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        if payload.get("kind") != expected_kind:
            raise ValueError("cursor kind does not match endpoint")
        return payload
    except Exception as exc:
        raise ApiError("invalid_cursor", "Cursor is invalid for this endpoint", 400) from exc


def _event_cursor(event: Event, sort: str) -> str:
    if sort == "latest":
        return _encode_cursor(
            "events:latest",
            {
                "last_updated_at": _serialize_datetime(event.last_updated_at),
                "id": str(event.id),
            },
        )
    return _encode_cursor(
        "events:heat",
        {
            "heat_score": event.heat_score,
            "created_at": _serialize_datetime(event.created_at),
            "id": str(event.id),
        },
    )


def _article_cursor(article: Article) -> str:
    return _encode_cursor(
        "event_articles",
        {
            "published_at": _serialize_datetime(article.published_at),
            "created_at": _serialize_datetime(article.created_at),
            "id": str(article.id),
        },
    )


def _apply_event_cursor(stmt: Select, cursor: str, sort: str) -> Select:
    payload = _decode_cursor(cursor, f"events:{sort}")
    event_id = UUID(payload["id"])
    if sort == "latest":
        last_updated_at = _parse_cursor_datetime(payload.get("last_updated_at"))
        if last_updated_at is None:
            return stmt.where(Event.last_updated_at.is_(None), Event.id > event_id)
        return stmt.where(
            or_(
                Event.last_updated_at < last_updated_at,
                and_(Event.last_updated_at == last_updated_at, Event.id > event_id),
                Event.last_updated_at.is_(None),
            )
        )
    created_at = _parse_cursor_datetime(payload.get("created_at"))
    heat_score = float(payload["heat_score"])
    return stmt.where(
        or_(
            Event.heat_score < heat_score,
            and_(Event.heat_score == heat_score, Event.created_at < created_at),
            and_(Event.heat_score == heat_score, Event.created_at == created_at, Event.id > event_id),
        )
    )


def _apply_article_cursor(stmt: Select, cursor: str) -> Select:
    payload = _decode_cursor(cursor, "event_articles")
    article_id = UUID(payload["id"])
    published_at = _parse_cursor_datetime(payload.get("published_at"))
    created_at = _parse_cursor_datetime(payload.get("created_at"))
    created_after_cursor = or_(
        Article.created_at < created_at,
        and_(Article.created_at == created_at, Article.id > article_id),
    )
    if published_at is None:
        return stmt.where(Article.published_at.is_(None), created_after_cursor)
    return stmt.where(
        or_(
            Article.published_at < published_at,
            and_(Article.published_at == published_at, created_after_cursor),
            Article.published_at.is_(None),
        )
    )


@router.get("")
async def list_events(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    region: str | None = None,
    language: str | None = None,
    category: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    min_heat: float | None = Query(None, ge=0, le=100),
    sort: str = "heat",
):
    if sort not in {"heat", "latest"}:
        raise ApiError("invalid_sort", "Sort must be either 'heat' or 'latest'", 400)
    stmt: Select = select(Event)
    if region:
        stmt = stmt.where(Event.region_primary == region)
    if category:
        stmt = stmt.where(Event.category == category)
    if language:
        stmt = stmt.join(Article, Article.event_id == Event.id).where(Article.language == language)
    if date_from:
        stmt = stmt.where(Event.last_updated_at >= date_from)
    if date_to:
        stmt = stmt.where(Event.last_updated_at <= date_to)
    if min_heat is not None:
        stmt = stmt.where(Event.heat_score >= min_heat)
    if cursor:
        stmt = _apply_event_cursor(stmt, cursor, sort)
    total_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = await db.scalar(total_stmt)
    if sort == "latest":
        stmt = stmt.order_by(Event.last_updated_at.desc().nullslast(), Event.id.asc())
    else:
        stmt = stmt.order_by(Event.heat_score.desc().nullslast(), Event.created_at.desc(), Event.id.asc())
    stmt = stmt.limit(limit)
    events = (await db.execute(stmt)).scalars().unique().all()
    next_cursor = _event_cursor(events[-1], sort) if len(events) == limit else None
    return envelope(
        [EventRead.model_validate(event).model_dump(mode="json") for event in events],
        total=total or 0,
        count=len(events),
        cursor=cursor,
        next_cursor=next_cursor,
    )


@router.post("")
async def create_event(payload: EventCreate, db: AsyncSession = Depends(get_db)):
    event = Event(**payload.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return envelope(EventRead.model_validate(event).model_dump(mode="json"))


@router.post("/cluster-new")
async def cluster_new_articles(limit: int = Query(200, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    result = await EventClusteringService(db).cluster_unassigned(limit=limit)
    return envelope(result)


@router.get("/{event_id}")
async def get_event(event_id: UUID, db: AsyncSession = Depends(get_db)):
    event = await db.get(Event, event_id)
    if not event:
        raise ApiError("event_not_found", "Event not found", 404)
    return envelope(EventRead.model_validate(event).model_dump(mode="json"))


@router.get("/{event_id}/articles")
async def get_event_articles(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    language: str | None = None,
    region: str | None = None,
):
    stmt = select(Article).options(selectinload(Article.source)).where(Article.event_id == event_id)
    if cursor:
        stmt = _apply_article_cursor(stmt, cursor)
    if language:
        stmt = stmt.where(Article.language == language)
    if region:
        stmt = stmt.join(Source, Source.id == Article.source_id).where(Source.region == region)
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    articles = (
        await db.execute(
            stmt.order_by(Article.published_at.desc().nullslast(), Article.created_at.desc()).limit(limit)
        )
    ).scalars().all()
    next_cursor = _article_cursor(articles[-1]) if len(articles) == limit else None
    return envelope(
        [ArticleRead.model_validate(article).model_dump(mode="json") for article in articles],
        total=total or 0,
        count=len(articles),
        cursor=cursor,
        next_cursor=next_cursor,
    )


@router.get("/{event_id}/analysis")
async def get_event_analysis(event_id: UUID, db: AsyncSession = Depends(get_db)):
    analysis = (
        await db.execute(select(EventAnalysis).where(EventAnalysis.event_id == event_id))
    ).scalar_one_or_none()
    if not analysis:
        raise ApiError("analysis_not_found", "Analysis not found", 404)
    return envelope(EventAnalysisRead.model_validate(analysis).model_dump(mode="json"))


@router.get("/{event_id}/contradictions")
async def get_event_contradictions(event_id: UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Contradiction).where(Contradiction.event_id == event_id))).scalars().all()
    return envelope([ContradictionRead.model_validate(row).model_dump(mode="json") for row in rows], total=len(rows))


@router.get("/{event_id}/timeline")
async def get_event_timeline(event_id: UUID, db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Article.published_at, Article.title_original, Article.external_url, Source.name, Source.region)
            .join(Source, Source.id == Article.source_id)
            .where(Article.event_id == event_id)
            .order_by(Article.published_at.asc().nullslast())
        )
    ).all()
    timeline = [
        {
            "published_at": published_at.isoformat() if published_at else None,
            "title": title,
            "url": url,
            "source": source,
            "region": region,
        }
        for published_at, title, url, source, region in rows
    ]
    return envelope(timeline, total=len(timeline))


@router.get("/{event_id}/stats")
async def get_event_stats(event_id: UUID, db: AsyncSession = Depends(get_db)):
    count = await db.scalar(select(func.count()).select_from(Article).where(Article.event_id == event_id))
    return envelope({"article_count": count or 0})


@router.post("/{event_id}/collect")
async def collect_event_articles(event_id: UUID, db: AsyncSession = Depends(get_db)):
    event = await db.get(Event, event_id)
    if not event:
        raise ApiError("event_not_found", "Event not found", 404)
    result = await ArticleIngestionService(db).collect_google_news_for_event(event)
    if await EventAnalysisService(db).should_reanalyze(event_id):
        process_event_pipeline.delay(str(event_id))
    await notify_event_update(event_id, {"type": "articles_collected", "payload": result})
    return envelope(result)


@router.post("/{event_id}/pipeline")
async def start_event_pipeline(event_id: UUID, db: AsyncSession = Depends(get_db)):
    event = await db.get(Event, event_id)
    if not event:
        raise ApiError("event_not_found", "Event not found", 404)
    result = process_event_pipeline.delay(str(event_id))
    return envelope({"task_id": result.id, "event_id": str(event_id), "status": "queued"})


@router.post("/{event_id}/merge")
async def merge_event(event_id: UUID, payload: EventMergeRequest, db: AsyncSession = Depends(get_db)):
    event = await EventManagementService(db).merge_events(event_id, payload.source_event_id)
    await notify_event_update(event_id, {"type": "event_merged", "source_event_id": str(payload.source_event_id)})
    return envelope(EventRead.model_validate(event).model_dump(mode="json"))


@router.post("/{event_id}/split")
async def split_event(event_id: UUID, payload: EventSplitRequest, db: AsyncSession = Depends(get_db)):
    event = await EventManagementService(db).split_event(event_id, payload.article_ids, payload.title)
    await notify_event_update(event_id, {"type": "event_split", "new_event_id": str(event.id)})
    return envelope(EventRead.model_validate(event).model_dump(mode="json"))
