"""Anthropic Claude LLM provider implementation."""

from __future__ import annotations

from anthropic import AsyncAnthropic

from app.config import settings
from app.services.llm.base import LLMProvider


class ClaudeProvider(LLMProvider):
    """Provider for Claude Sonnet models."""

    def __init__(self, model: str = "claude-3-5-sonnet-latest") -> None:
        self.model = model
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        response = await self.client.messages.create(
            model=kwargs.get("model", self.model),
            max_tokens=kwargs.get("max_tokens", 2048),
            temperature=kwargs.get("temperature", 0.2),
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if hasattr(block, "text"))

