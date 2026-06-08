"""OpenAI LLM provider implementation."""

from __future__ import annotations

from openai import AsyncOpenAI

from app.config import settings
from app.services.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI chat models."""

    def __init__(self, model: str = "gpt-4o") -> None:
        self.model = model
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

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

