"""Tests for LLM provider runtime fallback behavior."""

from __future__ import annotations

from importlib.util import find_spec
import unittest

if not find_spec("openai") or not find_spec("anthropic"):
    raise unittest.SkipTest("LLM provider dependencies are not installed")

from app.services.llm.base import LLMProvider
from app.services.llm.base import EchoLLMProvider
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

    async def test_echo_provider_returns_structured_fact_fallback(self) -> None:
        provider = EchoLLMProvider()

        result = await provider.complete("system", "Title: Air base was struck\nExtract facts")

        self.assertIn("Air base was struck", result)
        self.assertIn("source_attribution", result)

    async def test_echo_provider_returns_readable_summary_fallback(self) -> None:
        provider = EchoLLMProvider()

        result = await provider.complete("system", "请撰写事件概要")

        self.assertIn("Multiple sources report", result)


if __name__ == "__main__":
    unittest.main()
