"""Celery analysis pipeline tasks."""

from __future__ import annotations

import asyncio
from uuid import UUID

from celery import chain
from redis import Redis
from sqlalchemy import delete, func, select

from app.api.v1.websocket import publish_event_update
from app.config import settings
from app.models.article import Article
from app.models.contradiction import Contradiction
from app.models.credibility import EventAnalysis
from app.models.event import Event
from app.models.fact_fragment import FactFragment
from app.services.analyzer.consensus_mapper import ConsensusMapper
from app.services.analyzer.contradiction_detector import ContradictionDetector
from app.services.analyzer.event_analysis_service import EventAnalysisService
from app.services.analyzer.fact_extractor import FactExtractor
from app.services.analyzer.narrative_analyzer import NarrativeAnalyzer
from app.services.processor.deduplicator import Deduplicator
from app.services.processor.translator import TranslationService
from app.tasks.celery_app import celery
from app.tasks.collect_task import collect_articles_for_event
from app.tasks.progress import set_progress
from app.tasks.worker_db import worker_session


PIPELINE_LOCK_TTL_SECONDS = 30 * 60


@celery.task(bind=True, name="app.tasks.analyze_task.translate_articles")
def translate_articles(self, payload: dict) -> dict:
    return asyncio.run(_translate_articles(self.request.id, payload))


@celery.task(
    bind=True,
    name="app.tasks.analyze_task.deduplicate_articles",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def deduplicate_articles(self, payload: dict) -> dict:
    return asyncio.run(_deduplicate_articles(self.request.id, payload))


@celery.task(bind=True, name="app.tasks.analyze_task.merge_group_results")
def merge_group_results(self, results: list) -> dict:
    """Merge Celery group result lists into one standard payload dict."""
    merged: dict = {}
    for result in results:
        if isinstance(result, dict):
            merged.update(result)
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, dict):
                    merged.update(item)
    return merged


@celery.task(
    bind=True,
    name="app.tasks.analyze_task.extract_facts",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def extract_facts(self, payload: dict) -> dict:
    return asyncio.run(_extract_facts(self.request.id, _event_id_from_payload(payload), payload))


@celery.task(
    bind=True,
    name="app.tasks.analyze_task.detect_contradictions",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def detect_contradictions(self, payload: dict) -> dict:
    return asyncio.run(_detect_contradictions(self.request.id, _event_id_from_payload(payload), payload))


@celery.task(
    bind=True,
    name="app.tasks.analyze_task.analyze_narratives",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def analyze_narratives(self, payload: dict) -> dict:
    return asyncio.run(_analyze_narratives(self.request.id, _event_id_from_payload(payload), payload))


@celery.task(
    bind=True,
    name="app.tasks.analyze_task.generate_consensus_map",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def generate_consensus_map(self, payload: dict) -> dict:
    return asyncio.run(_generate_consensus_map(self.request.id, _event_id_from_payload(payload), payload))


@celery.task(
    bind=True,
    name="app.tasks.analyze_task.notify_clients",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def notify_clients(self, payload: dict) -> dict:
    return asyncio.run(_notify_clients(self.request.id, payload))


@celery.task(
    bind=True,
    name="app.tasks.analyze_task.scan_events_needing_analysis",
    autoretry_for=(),
)
def scan_events_needing_analysis(self, limit: int = 20) -> dict:
    """Queue analysis for active events that lack or need refreshed analysis."""
    return asyncio.run(_scan_events_needing_analysis(self.request.id, limit))


@celery.task(name="app.tasks.analyze_task.process_event_pipeline")
def process_event_pipeline(event_id: str) -> str:
    """Run the documented event processing pipeline in dependency order."""
    if not _acquire_pipeline_lock(event_id):
        return "skipped:locked"
    workflow = chain(
        collect_articles_for_event.s(event_id),
        deduplicate_articles.s(),
        extract_facts.s(),
        detect_contradictions.s(),
        analyze_narratives.s(),
        generate_consensus_map.s(),
        notify_clients.s(),
    )
    result = workflow.apply_async()
    return result.id


def _event_id_from_payload(payload: dict | list) -> str:
    """Recover event id from normal or Celery group payloads."""
    if isinstance(payload, dict):
        return str(payload.get("event_id", ""))
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and item.get("event_id"):
                return str(item["event_id"])
    return ""


async def _translate_articles(task_id: str, payload: dict) -> dict:
    event_id = _event_id_from_payload(payload)
    set_progress(task_id, status="running", step="translate_articles", event_id=event_id)
    if not event_id:
        return {**payload, "translated": False}
    async with worker_session() as db:
        articles = (
            await db.execute(
                select(Article).where(Article.event_id == UUID(event_id), Article.content_translated.is_(None))
            )
        ).scalars().all()
        translator = TranslationService()
        translated = 0
        for article in articles:
            article.title_translated = await translator.translate_article(article.title_original, article.language, "en")
            article.content_translated = await translator.translate_article(article.content_original, article.language, "en")
            translated += 1
        await db.commit()
    set_progress(task_id, status="complete", step="translate_articles", translated=translated, event_id=event_id)
    return {**payload, "event_id": event_id, "translated": translated}


async def _deduplicate_articles(task_id: str, payload: dict) -> dict:
    event_id = _event_id_from_payload(payload)
    set_progress(task_id, status="running", step="deduplicate_articles", event_id=event_id)
    if not event_id:
        return {**payload, "deduplicated": False}
    deduplicator = Deduplicator()
    duplicates = 0
    wire_copies = 0
    canonical_articles: list[Article] = []
    duplicate_article_ids: list[UUID] = []
    wire_by_article_id: dict[UUID, str] = {}
    async with worker_session() as db:
        articles = (
            await db.execute(
                select(Article)
                .where(Article.event_id == UUID(event_id))
                .order_by(Article.published_at.asc().nullsfirst(), Article.created_at.asc())
            )
        ).scalars().all()
        for article in articles:
            metadata = dict(article.article_metadata or {})
            wire_agency = deduplicator.detect_wire_copy(article.content_original)
            if wire_agency:
                metadata["wire_agency"] = wire_agency
                wire_by_article_id[article.id] = wire_agency
                wire_copies += 1
            duplicate_of = next(
                (
                    canonical
                    for canonical in canonical_articles
                    if deduplicator.is_content_duplicate(canonical.content_original, article.content_original)
                ),
                None,
            )
            if duplicate_of:
                metadata["duplicate_of"] = str(duplicate_of.id)
                metadata["duplicate_reason"] = "content_similarity"
                duplicate_article_ids.append(article.id)
                duplicates += 1
            else:
                canonical_articles.append(article)
            article.article_metadata = metadata
        if duplicate_article_ids:
            await db.execute(delete(FactFragment).where(FactFragment.article_id.in_(duplicate_article_ids)))
        if wire_by_article_id:
            wire_article_ids = list(wire_by_article_id)
            existing_fragments = (
                await db.execute(select(FactFragment).where(FactFragment.article_id.in_(wire_article_ids)))
            ).scalars().all()
            for fragment in existing_fragments:
                wire_agency = wire_by_article_id.get(fragment.article_id)
                if not wire_agency:
                    continue
                fragment.entities = {**(fragment.entities or {}), "_via_wire": wire_agency}
        await db.commit()
    set_progress(
        task_id,
        status="complete",
        step="deduplicate_articles",
        event_id=event_id,
        duplicates=duplicates,
        wire_copies=wire_copies,
    )
    return {**payload, "event_id": event_id, "deduplicated": True, "duplicates": duplicates, "wire_copies": wire_copies}


async def _extract_facts(task_id: str, event_id: str, payload: dict | list) -> dict:
    set_progress(task_id, status="running", step="extract_facts", event_id=event_id)
    async with worker_session() as db:
        already_extracted = select(FactFragment.article_id).where(FactFragment.event_id == UUID(event_id))
        articles = (
            await db.execute(
                select(Article)
                .where(Article.event_id == UUID(event_id), Article.id.not_in(already_extracted))
                .order_by(Article.published_at.asc().nullsfirst(), Article.created_at.asc())
            )
        ).scalars().all()
        fragments = await EventAnalysisService(db)._extract_fragments(UUID(event_id), articles)
        db.add_all(fragments)
        total_fragments = await db.scalar(
            select(func.count()).select_from(FactFragment).where(FactFragment.event_id == UUID(event_id))
        )
        await db.commit()
    total = total_fragments or 0
    set_progress(task_id, status="complete", step="extract_facts", new_fragments=len(fragments), total_fragments=total, event_id=event_id)
    return {"event_id": event_id, "new_fragments": len(fragments), "facts_extracted": total, "previous": payload}


async def _detect_contradictions(task_id: str, event_id: str, payload: dict) -> dict:
    set_progress(task_id, status="running", step="detect_contradictions", event_id=event_id)
    async with worker_session() as db:
        fragments = (
            await db.execute(select(FactFragment).where(FactFragment.event_id == UUID(event_id)))
        ).scalars().all()
        contradictions = await ContradictionDetector().detect_all_from_fragments(UUID(event_id), fragments)
        await db.execute(delete(Contradiction).where(Contradiction.event_id == UUID(event_id)))
        db.add_all(contradictions)
        await db.commit()
    set_progress(
        task_id,
        status="complete",
        step="detect_contradictions",
        contradictions=len(contradictions),
        event_id=event_id,
    )
    return {**payload, "contradictions_detected": len(contradictions)}


async def _analyze_narratives(task_id: str, event_id: str, payload: dict) -> dict:
    set_progress(task_id, status="running", step="analyze_narratives", event_id=event_id)
    async with worker_session() as db:
        articles = (await db.execute(select(Article).where(Article.event_id == UUID(event_id)))).scalars().all()
        frames = await NarrativeAnalyzer().compare_frames(UUID(event_id), articles)
    set_progress(task_id, status="complete", step="analyze_narratives", frames=len(frames), event_id=event_id)
    return {**payload, "narrative_frames": frames}


async def _generate_consensus_map(task_id: str, event_id: str, payload: dict) -> dict:
    set_progress(task_id, status="running", step="generate_consensus_map", event_id=event_id)
    async with worker_session() as db:
        fragments = (
            await db.execute(select(FactFragment).where(FactFragment.event_id == UUID(event_id)))
        ).scalars().all()
        article_count = await db.scalar(select(func.count()).select_from(Article).where(Article.event_id == UUID(event_id)))
        contradictions = (
            await db.execute(select(Contradiction).where(Contradiction.event_id == UUID(event_id)))
        ).scalars().all()
        data = await ConsensusMapper().generate_analysis_payload(
            UUID(event_id),
            fragments,
            contradictions,
            payload.get("narrative_frames", []),
            article_count_at_analysis=article_count or 0,
        )
        existing = (
            await db.execute(select(EventAnalysis).where(EventAnalysis.event_id == UUID(event_id)))
        ).scalar_one_or_none()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            analysis = existing
        else:
            analysis = EventAnalysis(**data)
            db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
    set_progress(task_id, status="complete", step="generate_consensus_map", analysis_id=str(analysis.id), event_id=event_id)
    return {**payload, "analysis_id": str(analysis.id), "consensus_generated": True}


async def _notify_clients(task_id: str, payload: dict) -> dict:
    event_id = _event_id_from_payload(payload)
    set_progress(task_id, status="running", step="notify_clients", event_id=event_id)
    message = {
        "event_id": event_id,
        "type": "analysis_updated",
        "payload": {
            "analysis_id": payload.get("analysis_id"),
            "consensus_generated": payload.get("consensus_generated", False),
            "contradictions_detected": payload.get("contradictions_detected"),
        },
    }
    if event_id:
        await publish_event_update(message)
        _release_pipeline_lock(event_id)
    set_progress(task_id, status="complete", step="notify_clients", event_id=event_id, notified=bool(event_id))
    return {**payload, "notified": bool(event_id)}


async def _scan_events_needing_analysis(task_id: str, limit: int) -> dict:
    set_progress(task_id, status="running", step="scan_events_needing_analysis", limit=limit)
    queued: list[str] = []
    async with worker_session() as db:
        rows = (
            await db.execute(
                select(Event, EventAnalysis)
                .outerjoin(EventAnalysis, EventAnalysis.event_id == Event.id)
                .where(Event.status == "active", Event.article_count > 0)
                .order_by(Event.last_updated_at.desc().nullslast(), Event.created_at.desc())
                .limit(limit * 4)
            )
        ).all()
        for event, analysis in rows:
            if len(queued) >= limit:
                break
            if not analysis:
                queued.append(str(event.id))
                continue
            previous_count = analysis.article_count_at_analysis or 0
            if previous_count == 0:
                queued.append(str(event.id))
                continue
            change_ratio = abs((event.article_count or 0) - previous_count) / previous_count
            if change_ratio > settings.reanalyze_threshold:
                queued.append(str(event.id))

    task_ids = []
    for event_id in queued:
        result = process_event_pipeline.delay(event_id)
        task_ids.append(result.id)
    summary = {"status": "ok", "events_scanned": len(rows), "queued": len(queued), "event_ids": queued, "task_ids": task_ids}
    set_progress(task_id, status="complete", step="scan_events_needing_analysis", result=summary)
    return summary


def _acquire_pipeline_lock(event_id: str) -> bool:
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        return bool(client.set(f"pipeline_lock:{event_id}", "1", nx=True, ex=PIPELINE_LOCK_TTL_SECONDS))
    except Exception:
        return True


def _release_pipeline_lock(event_id: str) -> None:
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        client.delete(f"pipeline_lock:{event_id}")
    except Exception:
        return
