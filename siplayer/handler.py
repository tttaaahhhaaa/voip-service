import hmac
import hashlib
import logging
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Callable, Coroutine
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    CALL = "call"
    SMS = "sms"


class IncomingMessage(BaseModel):
    type: MessageType
    source: str
    destination: str
    text: Optional[str] = None
    call_id: str = Field(default_factory=lambda: f"call-{datetime.utcnow().timestamp()}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SIPWebhookHandler:

    def __init__(self, webhook_secret: str = ""):
        self._webhook_secret = webhook_secret
        self._callbacks: dict[MessageType, list[Callable]] = {
            MessageType.CALL: [],
            MessageType.SMS: [],
        }

    def on_call(self, handler: Callable[[IncomingMessage], Coroutine]):
        self._callbacks[MessageType.CALL].append(handler)
        return handler

    def on_sms(self, handler: Callable[[IncomingMessage], Coroutine]):
        self._callbacks[MessageType.SMS].append(handler)
        return handler

    async def handle_webhook(self, request: Request) -> dict:
        if self._webhook_secret:
            await self._verify_signature(request)

        payload = await request.json()
        message = self._parse_payload(payload)

        for cb in self._callbacks.get(message.type, []):
            await cb(message)

        return {"status": "ok", "message_id": message.call_id}

    async def _verify_signature(self, request: Request):
        sig = request.headers.get("X-Signature-256", "")
        body = await request.body()
        expected = hmac.new(
            self._webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=403, detail="Invalid signature")

    def _parse_payload(self, payload: dict) -> IncomingMessage:
        msg_type = MessageType.SMS if "text" in payload or "body" in payload else MessageType.CALL
        return IncomingMessage(
            type=msg_type,
            source=payload.get("from", payload.get("source", "unknown")),
            destination=payload.get("to", payload.get("destination", "unknown")),
            text=payload.get("text", payload.get("body")),
            call_id=payload.get("call_id", payload.get("id", "")),
        )
