"""Ollama local-model provider implementation."""

from __future__ import annotations

import httpx

from app.config import settings
from app.services.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Provider for locally hosted Ollama models."""

    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/generate",
                json={
                    "model": kwargs.get("model", settings.ollama_model),
                    "prompt": f"{system_prompt}\n\n{user_prompt}",
                    "stream": False,
                    "options": {"temperature": kwargs.get("temperature", 0.2)},
                },
            )
            response.raise_for_status()
            return response.json().get("response", "")

