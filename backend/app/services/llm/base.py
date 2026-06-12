"""Unified LLM provider interface used by all AI-facing services."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json


class LLMProvider(ABC):
    """Pluggable async LLM provider contract."""

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Return a text completion."""

    async def complete_json(self, system_prompt: str, user_prompt: str, schema: dict) -> dict:
        """Return JSON, validating only that output can be parsed as an object."""
        raw = await self.complete(
            system_prompt,
            f"{user_prompt}\n\nReturn only JSON matching this schema:\n{json.dumps(schema)}",
        )
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1:
                raise
            value = json.loads(raw[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("LLM JSON output must be an object")
        return value


class EchoLLMProvider(LLMProvider):
    """Deterministic local fallback used when no external provider is configured."""

    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        if "翻译" in user_prompt or "translate" in user_prompt.lower():
            return user_prompt.split("原文：")[-1].strip() if "原文：" in user_prompt else user_prompt
        if "事实" in user_prompt or "fact" in user_prompt.lower() or "extract" in user_prompt.lower():
            title_line = ""
            for line in user_prompt.split("\n"):
                if "标题" in line or "title" in line.lower():
                    title_line = line.split("：")[-1].split(":")[-1].strip()
                    break
            if not title_line:
                title_line = user_prompt[:100].strip()
            return json.dumps(
                [
                    {
                        "type": "what",
                        "content": title_line,
                        "content_en": title_line,
                        "entities": {},
                        "numbers": {},
                        "source_attribution": "unattributed",
                        "certainty_level": "reportedly",
                    }
                ],
                ensure_ascii=False,
            )
        if "框架" in user_prompt or "frame" in user_prompt.lower() or "narrative" in user_prompt.lower():
            return json.dumps(
                {
                    "frames": ["一般新闻报道"],
                    "angle": "事实报道",
                    "emphasis": [],
                    "downplayed": [],
                    "tone": "中性",
                    "wording": [],
                },
                ensure_ascii=False,
            )
        if "概要" in user_prompt or "summary" in user_prompt.lower() or "编辑" in user_prompt:
            return "多个来源报道了同一事件，但关键细节仍需进一步核实。"
        return "{}"
