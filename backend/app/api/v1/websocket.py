"""WebSocket connection manager and Redis fan-out for live event updates."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.config import settings

router = APIRouter()
EVENT_UPDATE_CHANNEL = "truthpuzzle:event_updates"


class ConnectionManager:
    """Track WebSocket clients by event id and broadcast update messages."""

    def __init__(self) -> None:
        self.active: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, event_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active[str(event_id)].append(websocket)

    def disconnect(self, event_id: UUID, websocket: WebSocket) -> None:
        clients = self.active[str(event_id)]
        if websocket in clients:
            clients.remove(websocket)

    async def broadcast(self, event_id: UUID, message: dict) -> None:
        for websocket in list(self.active[str(event_id)]):
            try:
                await websocket.send_json(message)
            except RuntimeError:
                self.disconnect(event_id, websocket)

    async def broadcast_payload(self, message: dict) -> None:
        event_id = message.get("event_id")
        if not event_id:
            return
        await self.broadcast(UUID(event_id), message)


manager = ConnectionManager()


async def notify_event_update(event_id: UUID, message: dict) -> None:
    """Broadcast locally and publish through Redis for other worker processes."""
    payload = {"event_id": str(event_id), **message}
    await manager.broadcast(event_id, payload)
    await publish_event_update(payload)


async def publish_event_update(message: dict) -> None:
    """Publish an event update for the API process to fan out to WebSocket clients."""
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        await client.publish(EVENT_UPDATE_CHANNEL, json.dumps(message))
        await client.aclose()
    except Exception:
        return


async def redis_event_listener() -> None:
    """Forward Redis-published event updates to in-process WebSocket clients."""
    while True:
        client: Redis | None = None
        try:
            client = Redis.from_url(settings.redis_url, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe(EVENT_UPDATE_CHANNEL)
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                except (TypeError, json.JSONDecodeError):
                    continue
                await manager.broadcast_payload(payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(2)
        finally:
            if client:
                await client.aclose()


@router.websocket("/events/{event_id}")
async def event_socket(websocket: WebSocket, event_id: UUID):
    await manager.connect(event_id, websocket)
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({"type": "heartbeat", "event_id": str(event_id)})
    except WebSocketDisconnect:
        manager.disconnect(event_id, websocket)
