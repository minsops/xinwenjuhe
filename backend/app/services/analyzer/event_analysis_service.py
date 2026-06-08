"""Transactional event analysis pipeline used by API routes and Celery tasks."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import ApiError
from app.models.article import Article
from app.models.contradiction import Contradiction
from app.models.credibility import EventAnalysis
from app.models.fact_fragment import FactFragment
from app.services.analyzer.consensus_mapper import ConsensusMapper
from app.services.analyzer.contradiction_detector import ContradictionDetector
from app.services.analyzer.fact_extractor import FactExtractor
from app.services.analyzer.narrative_analyzer import NarrativeAnalyzer
from app.services.clustering.embedder import TextEmbedder


class EventAnalysisService:
    """Run fact extraction, contradiction detection, framing, and consensus mapping."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run(self, event_id: UUID) -> EventAnalysis:
        """Regenerate the complete analysis record for one event."""
        articles = (await self.db.execute(select(Article).where(Article.event_id == event_id))).scalars().all()
        if not articles:
            raise ApiError("no_articles", "Event has no articles to analyze", 400)

        fragments = await self._extract_fragments(event_id, articles)
        await self.db.execute(delete(FactFragment).where(FactFragment.event_id == event_id))
        self.db.add_all(fragments)
        await self.db.flush()

        detector = ContradictionDetector()
        contradictions = await detector.detect_all_from_fragments(event_id, fragments)
        narrative_frames = await NarrativeAnalyzer().compare_frames(event_id, articles)

        await self.db.execute(delete(Contradiction).where(Contradiction.event_id == event_id))
        self.db.add_all(contradictions)
        await self.db.flush()

        payload = await ConsensusMapper().generate_analysis_payload(
            event_id, fragments, contradictions, narrative_frames, article_count_at_analysis=len(articles)
        )
        existing = (
            await self.db.execute(select(EventAnalysis).where(EventAnalysis.event_id == event_id))
        ).scalar_one_or_none()
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            analysis = existing
        else:
            analysis = EventAnalysis(**payload)
            self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)
        return analysis

    async def should_reanalyze(self, event_id: UUID) -> bool:
        """Return true when article volume changed beyond the configured threshold."""
        article_count = await self.db.scalar(select(func.count()).select_from(Article).where(Article.event_id == event_id))
        analysis = (
            await self.db.execute(select(EventAnalysis).where(EventAnalysis.event_id == event_id))
        ).scalar_one_or_none()
        if not analysis:
            return bool(article_count)
        previous_count = analysis.article_count_at_analysis or 0
        if previous_count == 0:
            return bool(article_count)
        change_ratio = abs((article_count or 0) - previous_count) / previous_count
        return change_ratio > settings.reanalyze_threshold

    async def _extract_fragments(self, event_id: UUID, articles: list[Article]) -> list[FactFragment]:
        extractor = FactExtractor()
        embedder = TextEmbedder()
        fragments: list[FactFragment] = []
        for article in articles:
            for item in await extractor.extract(article):
                content = item.get("content", "").strip()
                if not content:
                    continue
                content_en = item.get("content_en") or content
                fragments.append(
                    FactFragment(
                        event_id=event_id,
                        article_id=article.id,
                        source_id=article.source_id,
                        fragment_type=item.get("type", "what"),
                        content=content,
                        content_en=content_en,
                        entities=item.get("entities") or {},
                        numbers=item.get("numbers") or {},
                        source_attribution=item.get("source_attribution", "unattributed"),
                        certainty_level=item.get("certainty_level", "reportedly"),
                        embedding=await embedder.embed_text(content_en),
                    )
                )
        return fragments
