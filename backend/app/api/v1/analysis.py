"""Analysis helper routes for triggering MVP analysis generation."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, envelope
from app.db import get_db
from app.schemas.analysis import EventAnalysisRead
from app.api.v1.websocket import notify_event_update
from app.services.analyzer.event_analysis_service import EventAnalysisService

router = APIRouter()


@router.post("/events/{event_id}/run")
async def run_event_analysis(event_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        analysis = await EventAnalysisService(db).run(event_id)
    except ApiError as exc:
        raise ApiError("no_articles", "Event has no articles to analyze", 400)
    await notify_event_update(event_id, {"type": "analysis_updated", "analysis_id": str(analysis.id)})
    return envelope(EventAnalysisRead.model_validate(analysis).model_dump(mode="json"))
