import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.engine.events import event_bus

router = APIRouter(tags=["stream"])


@router.websocket("/stream")
async def ws_stream(websocket: WebSocket):
    await websocket.accept()
    queue = event_bus.subscribe()
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25.0)
                await websocket.send_text(json.dumps({"type": event.type, "payload": event.payload}))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe(queue)
