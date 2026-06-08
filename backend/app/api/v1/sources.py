"""Media source routes."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ApiError, envelope
from app.db import get_db
from app.models.article import Article
from app.models.source import Source
from app.schemas.article import ArticleRead
from app.schemas.source import SourceRead
from app.services.analyzer.credibility_scorer import CredibilityScorer
from app.services.collector.ingestion import ArticleIngestionService
from app.tasks.credibility_task import refresh_source_credibility

router = APIRouter()


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


def _source_cursor(source: Source) -> str:
    return _encode_cursor(
        "sources",
        {
            "region": source.region,
            "name": source.name,
            "id": str(source.id),
        },
    )


def _source_article_cursor(article: Article) -> str:
    return _encode_cursor(
        "source_articles",
        {
            "published_at": _serialize_datetime(article.published_at),
            "created_at": _serialize_datetime(article.created_at),
            "id": str(article.id),
        },
    )


def _apply_source_cursor(stmt, cursor: str):
    payload = _decode_cursor(cursor, "sources")
    source_id = UUID(payload["id"])
    region = str(payload["region"])
    name = str(payload["name"])
    return stmt.where(
        or_(
            Source.region > region,
            and_(Source.region == region, Source.name > name),
            and_(Source.region == region, Source.name == name, Source.id > source_id),
        )
    )


def _apply_source_article_cursor(stmt, cursor: str):
    payload = _decode_cursor(cursor, "source_articles")
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
async def list_sources(
    db: AsyncSession = Depends(get_db),
    region: str | None = None,
    language: str | None = None,
    limit: int = Query(100, ge=1, le=200),
    cursor: str | None = None,
):
    stmt = select(Source)
    if region:
        stmt = stmt.where(Source.region == region)
    if language:
        stmt = stmt.where(Source.language == language)
    if cursor:
        stmt = _apply_source_cursor(stmt, cursor)
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = (await db.execute(stmt.order_by(Source.region, Source.name, Source.id).limit(limit))).scalars().all()
    next_cursor = _source_cursor(rows[-1]) if len(rows) == limit else None
    return envelope(
        [SourceRead.model_validate(row).model_dump(mode="json") for row in rows],
        total=total or 0,
        count=len(rows),
        cursor=cursor,
        next_cursor=next_cursor,
    )


@router.get("/{source_id}")
async def get_source(source_id: UUID, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise ApiError("source_not_found", "Source not found", 404)
    return envelope(SourceRead.model_validate(source).model_dump(mode="json"))


@router.get("/{source_id}/articles")
async def get_source_articles(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
):
    stmt = select(Article).options(selectinload(Article.source)).where(Article.source_id == source_id)
    if cursor:
        stmt = _apply_source_article_cursor(stmt, cursor)
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = (
        await db.execute(
            stmt.order_by(Article.published_at.desc().nullslast(), Article.created_at.desc(), Article.id.asc()).limit(limit)
        )
    ).scalars().all()
    next_cursor = _source_article_cursor(rows[-1]) if len(rows) == limit else None
    return envelope(
        [ArticleRead.model_validate(row).model_dump(mode="json") for row in rows],
        total=total or 0,
        count=len(rows),
        cursor=cursor,
        next_cursor=next_cursor,
    )


@router.post("/{source_id}/collect")
async def collect_source(source_id: UUID, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise ApiError("source_not_found", "Source not found", 404)
    result = await ArticleIngestionService(db).collect_source(source)
    return envelope(result)


@router.post("/{source_id}/refresh-credibility")
async def refresh_one_source_credibility(source_id: UUID, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise ApiError("source_not_found", "Source not found", 404)
    await CredibilityScorer().update_source_scores(source)
    await db.commit()
    await db.refresh(source)
    return envelope(SourceRead.model_validate(source).model_dump(mode="json"))


@router.post("/refresh-credibility")
async def refresh_all_source_credibility():
    result = refresh_source_credibility.delay()
    return envelope({"task_id": result.id, "status": "queued"})
