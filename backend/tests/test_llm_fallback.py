"""Tests for LLM provider runtime fallback behavior."""

from __future__ import annotations

from importlib.util import find_spec
import unittest

if not find_spec("openai") or not find_spec("anthropic"):
    raise unittest.SkipTest("LLM provider dependencies are not installed")

from app.services.llm.base import LLMProvider
from app.services.llm.factory import FallbackLLMProvider


class FailingProvider(LLMProvider):
    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        raise RuntimeError("provider failed")


class WorkingProvider(LLMProvider):
    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        return "ok"


class LLMFallbackTest(unittest.IsolatedAsyncioTestCase):
    """Validate fallback chains move past failed providers."""

    async def test_complete_falls_back_to_next_provider(self) -> None:
        provider = FallbackLLMProvider([FailingProvider(), WorkingProvider()])

        result = await provider.complete("system", "user")

        self.assertEqual(result, "ok")


if __name__ == "__main__":
    unittest.main()
