"""Analysis helper routes for queueing event analysis generation."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, envelope
from app.db import get_db
from app.api.v1.websocket import notify_event_update
from app.models.event import Event
from app.tasks.analyze_task import process_event_pipeline

router = APIRouter()


@router.post("/events/{event_id}/run")
async def run_event_analysis(event_id: UUID, db: AsyncSession = Depends(get_db)):
    event = await db.get(Event, event_id)
    if not event:
        raise ApiError("event_not_found", "Event not found", 404)
    result = process_event_pipeline.delay(str(event_id))
    await notify_event_update(event_id, {"type": "analysis_queued", "task_id": result.id})
    return envelope({"task_id": result.id, "event_id": str(event_id), "status": "queued"})
