"""Factory and fallback chain for LLM providers."""

from __future__ import annotations

from app.config import settings
from app.services.llm.base import EchoLLMProvider, LLMProvider
from app.services.llm.claude_provider import ClaudeProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.openai_provider import OpenAIProvider


class FallbackLLMProvider(LLMProvider):
    """Try providers in order, falling back when one fails at runtime."""

    def __init__(self, providers: list[LLMProvider]) -> None:
        self.providers = providers or [EchoLLMProvider()]

    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        last_error: Exception | None = None
        for provider in self.providers:
            try:
                return await provider.complete(system_prompt, user_prompt, **kwargs)
            except Exception as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        return ""


def get_llm_provider() -> LLMProvider:
    """Create the configured provider chain with a deterministic final fallback."""
    provider = settings.llm_provider.lower()
    providers: list[LLMProvider] = []
    if provider == "openai" and settings.openai_api_key:
        providers.append(OpenAIProvider())
    if provider == "claude" and settings.anthropic_api_key:
        providers.append(ClaudeProvider())
    if provider == "ollama":
        providers.append(OllamaProvider())
    if provider != "openai" and settings.openai_api_key:
        providers.append(OpenAIProvider())
    if provider != "claude" and settings.anthropic_api_key:
        providers.append(ClaudeProvider())
    if provider != "ollama":
        providers.append(OllamaProvider())
    providers.append(EchoLLMProvider())
    return FallbackLLMProvider(providers)
