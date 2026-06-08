"""Top-level API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import analysis, articles, discovery, events, search, sources, tasks, websocket

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(articles.router, prefix="/articles", tags=["articles"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(discovery.router, prefix="/discovery", tags=["discovery"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
