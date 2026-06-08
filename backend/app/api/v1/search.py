"""Simple multilingual search route."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import envelope
from app.db import get_db
from app.services.search import SearchService

router = APIRouter()


@router.get("")
async def search_articles(
    q: str = Query(..., min_length=1),
    lang: str | None = None,
    region: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await SearchService(db).search(
        query=q,
        lang=lang,
        region=region,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return envelope(
        result,
        article_count=len(result["articles"]),
        event_count=len(result["events"]),
        region=region,
        lang=lang,
    )
