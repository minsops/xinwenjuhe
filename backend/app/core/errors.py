"""Shared API exception types and handlers."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Domain error returned in the API's standard error envelope."""

    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    """Render domain errors using the documented error shape."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


def envelope(data, **meta):
    """Return the documented success response envelope."""
    return {"data": data, "meta": meta}

