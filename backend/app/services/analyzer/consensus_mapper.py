"""Consensus, dispute, and blind-spot map generation."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from app.config import settings
from app.models.contradiction import Contradiction
from app.models.fact_fragment import FactFragment


class ConsensusMapper:
    """Generate the right-panel known/disputed/blind-spot analysis map."""

    async def generate_analysis_payload(
        self,
        event_id: UUID,
        fragments: list[FactFragment],
        contradictions: list[Contradiction],
        narrative_frames: list[dict] | None = None,
        article_count_at_analysis: int | None = None,
    ) -> dict:
        source_ids = {fragment.source_id for fragment in fragments}
        analyzed_article_count = article_count_at_analysis
        if analyzed_article_count is None:
            analyzed_article_count = len({fragment.article_id for fragment in fragments})
        total = max(len(source_ids), 1)
        by_content: dict[str, set[UUID]] = defaultdict(set)
        article_ids: dict[str, list[str]] = defaultdict(list)
        for fragment in fragments:
            by_content[fragment.content].add(fragment.source_id)
            article_ids[fragment.content].append(str(fragment.article_id))

        consensus = [
            {
                "fact": fact,
                "confirmed_by": len(sources),
                "total": total,
                "source_ids": [str(source_id) for source_id in sources],
                "article_ids": article_ids[fact],
            }
            for fact, sources in by_content.items()
            if len(sources) / total >= settings.consensus_threshold
        ]
        disputed = [
            {
                "topic": contradiction.description,
                "type": contradiction.contradiction_type,
                "severity": contradiction.severity,
                "details": contradiction.details,
            }
            for contradiction in contradictions
        ]
        blind_spots = [
            {"description": fact, "mentioned_by": len(sources), "total": total}
            for fact, sources in by_content.items()
            if len(sources) / total < 0.3
        ]
        summary = self._summary(consensus, disputed, total)
        return {
            "event_id": event_id,
            "summary": summary,
            "consensus_facts": consensus,
            "disputed_facts": disputed,
            "blind_spots": blind_spots,
            "narrative_frames": narrative_frames or [],
            "source_graph": self._source_graph(fragments, contradictions),
            "timeline": self._timeline(fragments),
            "article_count_at_analysis": analyzed_article_count,
        }

    @staticmethod
    def _summary(consensus: list[dict], disputed: list[dict], total: int) -> str:
        if consensus:
            return f"Based on {total} source(s), the strongest common fact is: {consensus[0]['fact']}"
        if disputed:
            return f"Sources describe the event with unresolved dispute: {disputed[0]['topic']}"
        return "Insufficient cross-source evidence is available for a stable event summary."

    @staticmethod
    def _timeline(fragments: list[FactFragment]) -> list[dict]:
        """Build a chronological timeline from timestamped fact fragments."""
        items = []
        for fragment in fragments:
            if not fragment.timestamp_mentioned:
                continue
            items.append(
                {
                    "timestamp": fragment.timestamp_mentioned.isoformat(),
                    "fact": fragment.content,
                    "fragment_type": fragment.fragment_type,
                    "article_id": str(fragment.article_id),
                    "source_id": str(fragment.source_id),
                }
            )
        return sorted(items, key=lambda item: item["timestamp"])

    @staticmethod
    def _source_graph(fragments: list[FactFragment], contradictions: list[Contradiction]) -> dict:
        """Build a lightweight source graph for propagation and conflict views."""
        source_ids = sorted({str(fragment.source_id) for fragment in fragments})
        nodes = [{"id": source_id, "type": "source"} for source_id in source_ids]
        edges = []
        for fragment in fragments:
            edges.append(
                {
                    "from": str(fragment.source_id),
                    "to": str(fragment.article_id),
                    "type": "reported",
                    "fragment_id": str(fragment.id),
                    "fragment_type": fragment.fragment_type,
                }
            )
        for contradiction in contradictions:
            related_sources = [str(source_id) for source_id in contradiction.source_ids]
            for source_id in related_sources:
                edges.append(
                    {
                        "from": source_id,
                        "to": str(contradiction.id),
                        "type": contradiction.contradiction_type,
                        "severity": contradiction.severity,
                    }
                )
            nodes.append(
                {
                    "id": str(contradiction.id),
                    "type": "contradiction",
                    "severity": contradiction.severity,
                }
            )
        return {"nodes": nodes, "edges": edges}
