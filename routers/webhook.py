from fastapi import APIRouter, Request
from siplayer import SIPWebhookHandler

router = APIRouter(prefix="/api/webhook", tags=["Webhook"])

sip_handler: SIPWebhookHandler = None


@router.post("/incoming")
async def incoming_webhook(request: Request):
    return await sip_handler.handle_webhook(request)
