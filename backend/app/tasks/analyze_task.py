"""Celery analysis pipeline tasks."""

from __future__ import annotations

import asyncio
from uuid import UUID

from celery import chain, group
from sqlalchemy import delete, func, select

from app.api.v1.websocket import publish_event_update
from app.db import AsyncSessionLocal
from app.models.article import Article
from app.models.contradiction import Contradiction
from app.models.credibility import EventAnalysis
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


@celery.task(bind=True, name="app.tasks.analyze_task.translate_articles")
def translate_articles(self, payload: dict) -> dict:
    return asyncio.run(_translate_articles(self.request.id, payload))


@celery.task(bind=True, name="app.tasks.analyze_task.deduplicate_articles")
def deduplicate_articles(self, payload: dict) -> dict:
    return asyncio.run(_deduplicate_articles(self.request.id, payload))


@celery.task(bind=True, name="app.tasks.analyze_task.extract_facts")
def extract_facts(self, payload: dict) -> dict:
    return asyncio.run(_extract_facts(self.request.id, _event_id_from_payload(payload), payload))


@celery.task(bind=True, name="app.tasks.analyze_task.detect_contradictions")
def detect_contradictions(self, payload: dict) -> dict:
    return asyncio.run(_detect_contradictions(self.request.id, _event_id_from_payload(payload), payload))


@celery.task(bind=True, name="app.tasks.analyze_task.analyze_narratives")
def analyze_narratives(self, payload: dict) -> dict:
    return asyncio.run(_analyze_narratives(self.request.id, _event_id_from_payload(payload), payload))


@celery.task(bind=True, name="app.tasks.analyze_task.generate_consensus_map")
def generate_consensus_map(self, payload: dict) -> dict:
    return asyncio.run(_generate_consensus_map(self.request.id, _event_id_from_payload(payload), payload))


@celery.task(bind=True, name="app.tasks.analyze_task.notify_clients")
def notify_clients(self, payload: dict) -> dict:
    return asyncio.run(_notify_clients(self.request.id, payload))


@celery.task(name="app.tasks.analyze_task.process_event_pipeline")
def process_event_pipeline(event_id: str) -> str:
    """Run the documented event processing pipeline in dependency order."""
    workflow = chain(
        collect_articles_for_event.s(event_id),
        group(translate_articles.s(), deduplicate_articles.s()),
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
    if isinstance(payload, list):
        for item in payload:
            event_id = _event_id_from_payload(item)
            if event_id:
                return event_id
        return ""
    return str(payload.get("event_id") or payload.get("result", {}).get("event_id") or "")


async def _translate_articles(task_id: str, payload: dict) -> dict:
    event_id = _event_id_from_payload(payload)
    set_progress(task_id, status="running", step="translate_articles", event_id=event_id)
    if not event_id:
        return {**payload, "translated": False}
    async with AsyncSessionLocal() as db:
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
    async with AsyncSessionLocal() as db:
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
                duplicates += 1
            else:
                canonical_articles.append(article)
            article.article_metadata = metadata
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
    async with AsyncSessionLocal() as db:
        articles = (await db.execute(select(Article).where(Article.event_id == UUID(event_id)))).scalars().all()
        fragments = await EventAnalysisService(db)._extract_fragments(UUID(event_id), articles)
        await db.execute(delete(FactFragment).where(FactFragment.event_id == UUID(event_id)))
        db.add_all(fragments)
        await db.commit()
    set_progress(task_id, status="complete", step="extract_facts", fragments=len(fragments), event_id=event_id)
    return {"event_id": event_id, "facts_extracted": len(fragments), "previous": payload}


async def _detect_contradictions(task_id: str, event_id: str, payload: dict) -> dict:
    set_progress(task_id, status="running", step="detect_contradictions", event_id=event_id)
    async with AsyncSessionLocal() as db:
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
    async with AsyncSessionLocal() as db:
        articles = (await db.execute(select(Article).where(Article.event_id == UUID(event_id)))).scalars().all()
        frames = await NarrativeAnalyzer().compare_frames(UUID(event_id), articles)
    set_progress(task_id, status="complete", step="analyze_narratives", frames=len(frames), event_id=event_id)
    return {**payload, "narrative_frames": frames}


async def _generate_consensus_map(task_id: str, event_id: str, payload: dict) -> dict:
    set_progress(task_id, status="running", step="generate_consensus_map", event_id=event_id)
    async with AsyncSessionLocal() as db:
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
    set_progress(task_id, status="complete", step="notify_clients", event_id=event_id, notified=bool(event_id))
    return {**payload, "notified": bool(event_id)}
