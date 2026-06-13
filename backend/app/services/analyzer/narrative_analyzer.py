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

以 JSON 格式输出，所有字段值必须使用简体中文。
字段：
- frames: 简体中文短标签数组
- angle: 简体中文核心角度
- emphasis: 简体中文数组
- downplayed: 简体中文数组
- tone: 简体中文
- wording: 简体中文数组
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
        frames = row.get("frames") or row.get("dominant_frames") or row.get("主导框架") or ["一般新闻报道"]
        if isinstance(frames, str):
            frames = [frames]
        emphasis = row.get("emphasis") or row.get("强调点") or []
        downplayed = row.get("downplayed") or row.get("淡化点") or []
        wording = row.get("wording") or row.get("关键措辞选择") or []
        return {
            "source_id": str(article.source_id),
            "article_id": str(article.id),
            "frames": [_zh_frame(str(frame)) for frame in frames if str(frame).strip()] or ["一般新闻报道"],
            "angle": str(row.get("angle") or row.get("核心叙事角度") or "事实报道"),
            "emphasis": emphasis if isinstance(emphasis, list) else [str(emphasis)],
            "downplayed": downplayed if isinstance(downplayed, list) else [str(downplayed)],
            "tone": _zh_frame(str(row.get("tone") or row.get("情感基调") or "中性")),
            "wording": wording if isinstance(wording, list) else [str(wording)],
        }


def _zh_frame(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    labels = {
        "news_report": "一般新闻报道",
        "factual report": "事实报道",
        "factual_report": "事实报道",
        "neutral": "中性",
        "critical": "批评",
        "alleged": "指称",
        "conflict": "冲突",
        "official_statement": "官方表述",
        "security": "安全事件",
        "security_incident": "安全事件",
        "attack": "袭击叙事",
        "responsibility": "责任归属",
        "external_responsibility": "外部责任",
        "official_claims": "官方说法",
        "official_uncertainty": "官方不确定性",
        "strong attribution": "强烈归责",
        "strong_attribution": "强烈归责",
        "humanitarian": "人道影响",
        "casualties": "伤亡规模",
        "casualty_claim": "伤亡主张",
        "verification_gap": "核验不足",
        "regional_tension": "地区紧张",
        "victim_frame": "受害者叙事",
        "aggressor_frame": "加害者叙事",
        "accountability": "追责叙事",
    }
    if normalized in labels:
        return labels[normalized]
    if "_" in normalized:
        return "其他框架"
    if any(char.isascii() and char.isalpha() for char in value):
        return "其他框架"
    return value
