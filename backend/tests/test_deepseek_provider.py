"""Tests for DeepSeek provider configuration."""

from __future__ import annotations

from importlib.util import find_spec
import unittest

if not find_spec("openai"):
    raise unittest.SkipTest("OpenAI SDK is required for DeepSeek provider tests")

from app.config import settings
from app.services.llm.deepseek_provider import DeepSeekProvider


class DeepSeekProviderTest(unittest.TestCase):
    """Validate DeepSeek provider uses configured defaults."""

    def test_provider_uses_configured_model(self) -> None:
        provider = DeepSeekProvider()

        self.assertEqual(provider.model, settings.deepseek_model)


if __name__ == "__main__":
    unittest.main()
