"""DeepSeek OpenAI-compatible LLM provider implementation."""

from __future__ import annotations

from openai import AsyncOpenAI

from app.config import settings
from app.services.llm.base import LLMProvider


class DeepSeekProvider(LLMProvider):
    """Provider for DeepSeek chat models through the OpenAI-compatible API."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.deepseek_model
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url.rstrip("/"),
        )

    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        response = await self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=kwargs.get("temperature", 0.2),
        )
        return response.choices[0].message.content or ""
