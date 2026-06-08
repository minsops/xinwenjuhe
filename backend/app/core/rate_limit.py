"""Redis-backed request rate limiting middleware."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply a small per-client rolling-window request limit."""

    def __init__(self, app, requests_per_minute: int = 120) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._memory: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.url.path in {"/health", "/docs", "/openapi.json"}:
            return await call_next(request)
        key = request.client.host if request.client else "anonymous"
        allowed = await self._allow(key)
        if not allowed:
            return Response(
                content='{"error":{"code":"rate_limited","message":"Too many requests","details":{}}}',
                status_code=429,
                media_type="application/json",
            )
        return await call_next(request)

    async def _allow(self, key: str) -> bool:
        redis_key = f"rate:{key}:{int(time.time() // 60)}"
        try:
            client = Redis.from_url(settings.redis_url, decode_responses=True)
            count = await client.incr(redis_key)
            if count == 1:
                await client.expire(redis_key, 90)
            await client.aclose()
            return count <= self.requests_per_minute
        except Exception:
            now = time.time()
            window = self._memory[key]
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= self.requests_per_minute:
                return False
            window.append(now)
            return True

