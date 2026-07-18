import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.did_pool import DIDPool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ws", tags=["WebSocket"])

did_pool: DIDPool = None


class ConnectionManager:

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[user_id] = ws
        logger.info(f"WebSocket connected: {user_id}")

    def disconnect(self, user_id: str):
        self._connections.pop(user_id, None)

    async def notify(self, user_id: str, event: str, data: dict):
        ws = self._connections.get(user_id)
        if ws:
            try:
                await ws.send_json({"event": event, "data": data})
            except Exception:
                self.disconnect(user_id)

    async def broadcast(self, event: str, data: dict):
        for uid in list(self._connections.keys()):
            await self.notify(uid, event, data)


manager = ConnectionManager()


@router.websocket("/{user_id}")
async def websocket_endpoint(ws: WebSocket, user_id: str):
    await manager.connect(user_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_json({"event": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WS error for {user_id}: {e}")
        manager.disconnect(user_id)
