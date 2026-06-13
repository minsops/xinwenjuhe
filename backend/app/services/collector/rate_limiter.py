"""Async per-domain request spacing for collectors."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse


class DomainRateLimiter:
    """Space request starts for each domain without blocking unrelated domains."""

    def __init__(self, delay_seconds: float) -> None:
        self.delay_seconds = max(0.0, float(delay_seconds))
        self._locks: dict[str, asyncio.Lock] = {}
        self._next_allowed_at: dict[str, float] = {}

    async def wait(self, url: str) -> None:
        """Wait until the URL's domain is allowed to start its next request."""
        if self.delay_seconds <= 0:
            return
        domain = self._domain_key(url)
        lock = self._locks.setdefault(domain, asyncio.Lock())
        async with lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            wait_seconds = self._next_allowed_at.get(domain, now) - now
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
                now = loop.time()
            self._next_allowed_at[domain] = now + self.delay_seconds

    @staticmethod
    def _domain_key(url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc.lower() or parsed.path.lower() or "unknown"
