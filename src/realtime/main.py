"""WebSocket real-time service — separate FastAPI app per ADR-008."""

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect

from src.config import get_settings
from src.realtime.auth import validate_ws_token
from src.realtime.connections import ConnectionManager
from src.realtime.pubsub import EventBridge

logger = structlog.get_logger()
manager = ConnectionManager()
bridge = EventBridge(manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    redis_url = getattr(settings, "redis_url", None) or ""
    if redis_url:
        await bridge.start(redis_url)
        asyncio.create_task(bridge.listen())
    yield
    await bridge.stop()


app = FastAPI(title="Bhapi Real-Time Service", lifespan=lifespan)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "connections": manager.get_connected_count(),
    }


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    """Main WebSocket endpoint. Connect with ?token=<jwt>."""
    # Validate token
    user = await validate_ws_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = user["user_id"]
    await manager.connect(websocket, user_id)

    # Auto-join user's group room
    if user.get("group_id"):
        manager.join_room(user_id, f"group:{user['group_id']}")

    # Send welcome message
    await manager.send_to_user(
        user_id,
        {
            "type": "welcome",
            "user_id": user_id,
        },
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "heartbeat":
                manager.heartbeat(user_id)
                await manager.send_to_user(user_id, {"type": "heartbeat_ack"})

            elif msg_type == "join_room":
                room = data.get("room", "")
                if room:
                    manager.join_room(user_id, room)

            elif msg_type == "leave_room":
                room = data.get("room", "")
                if room:
                    manager.leave_room(user_id, room)

            elif msg_type == "message":
                # Relay to target user or room
                target = data.get("target_user_id")
                room = data.get("room")
                payload = {
                    "type": "message",
                    "from": user_id,
                    "data": data.get("data"),
                }
                if target:
                    await manager.send_to_user(target, payload)
                elif room:
                    await manager.broadcast_room(room, payload, exclude=user_id)

    except WebSocketDisconnect:
        await manager.disconnect(user_id)
    except Exception as e:
        logger.error("ws_error", user_id=user_id, error=str(e))
        await manager.disconnect(user_id)
