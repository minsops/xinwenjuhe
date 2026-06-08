"""FastAPI application entry point for TruthPuzzle."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.v1.websocket import redis_event_listener
from app.config import settings
from app.core.errors import ApiError, api_error_handler
from app.core.rate_limit import RateLimitMiddleware


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(api_router)
    listener_task: asyncio.Task | None = None

    @app.on_event("startup")
    async def start_event_listener() -> None:
        nonlocal listener_task
        listener_task = asyncio.create_task(redis_event_listener())

    @app.on_event("shutdown")
    async def stop_event_listener() -> None:
        if listener_task:
            listener_task.cancel()

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": {"errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": str(exc), "details": {}}},
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
