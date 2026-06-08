"""Narrative frame analysis for individual articles and whole events."""

from __future__ import annotations

import json
from uuid import UUID

from app.models.article import Article
from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_llm_provider


class NarrativeAnalyzer:
    """Analyze dominant frames, emphasis, omissions, tone, and wording."""

    FRAME_ANALYSIS_PROMPT = """
分析以下新闻报道的叙事框架。识别：
1. 主导框架
2. 核心叙事角度
3. 强调点
4. 淡化点
5. 情感基调
6. 关键措辞选择

以 JSON 格式输出。
"""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()

    async def analyze_article(self, article: Article) -> dict:
        raw = await self.llm.complete(
            "Analyze news narrative frames.",
            f"{self.FRAME_ANALYSIS_PROMPT}\n标题：{article.title_original}\n正文：{article.content_original[:5000]}",
        )
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {}
        return self._validate_frame(parsed, article)

    async def compare_frames(self, event_id: UUID, articles: list[Article] | None = None) -> list[dict]:
        if not articles:
            return []
        return [await self.analyze_article(article) for article in articles]

    @staticmethod
    def _validate_frame(row: dict, article: Article) -> dict:
        """Normalize LLM frame output into the documented frontend structure."""
        if not isinstance(row, dict):
            row = {}
        frames = row.get("frames") or row.get("dominant_frames") or row.get("主导框架") or ["news_report"]
        if isinstance(frames, str):
            frames = [frames]
        emphasis = row.get("emphasis") or row.get("强调点") or []
        downplayed = row.get("downplayed") or row.get("淡化点") or []
        wording = row.get("wording") or row.get("关键措辞选择") or []
        return {
            "source_id": str(article.source_id),
            "article_id": str(article.id),
            "frames": [str(frame) for frame in frames if str(frame).strip()] or ["news_report"],
            "angle": str(row.get("angle") or row.get("核心叙事角度") or "factual report"),
            "emphasis": emphasis if isinstance(emphasis, list) else [str(emphasis)],
            "downplayed": downplayed if isinstance(downplayed, list) else [str(downplayed)],
            "tone": str(row.get("tone") or row.get("情感基调") or "neutral"),
            "wording": wording if isinstance(wording, list) else [str(wording)],
        }
