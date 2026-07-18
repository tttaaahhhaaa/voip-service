import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from config import Settings
from siplayer import SIPWebhookHandler, IncomingMessage, MessageType
from services.did_pool import DIDPool
from services.async_processor import AsyncCDRProcessor
from services.sms_parser import SMSCodeExtractor
from models import CallDetailRecord, CDRType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = Settings()
did_pool = DIDPool(default_timeout_minutes=settings.DID_ALLOCATION_TIMEOUT_MINUTES)
sip_handler = SIPWebhookHandler(webhook_secret=settings.SIP_WEBHOOK_SECRET)
cdr_processor = AsyncCDRProcessor()
ws_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ws_manager

    logger.info(f"Starting {settings.APP_NAME}")

    from routers.ws import manager as ws_mgr
    ws_manager = ws_mgr

    sample_numbers = [f"+90555{d + 100000:06d}" for d in range(settings.DID_POOL_SIZE)]
    did_pool.load_pool(sample_numbers)

    cdr_processor.register_handler(handle_cdr)
    cdr_processor.start()

    sip_handler.on_call(handle_incoming_call)
    sip_handler.on_sms(handle_incoming_sms)

    import routers.did as did_router
    import routers.ws as ws_router
    did_router.did_pool = did_pool
    ws_router.did_pool = did_pool

    logger.info(f"DID pool initialized with {len(sample_numbers)} numbers")
    yield

    await cdr_processor.stop()
    logger.info("Application shutdown complete")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

from routers.did import router as did_router
from routers.webhook import router as webhook_router
from routers.ws import router as ws_router

app.include_router(did_router)
app.include_router(webhook_router)
app.include_router(ws_router)

import routers.webhook as webhook_rtr
webhook_rtr.sip_handler = sip_handler


async def handle_cdr(cdr: CallDetailRecord):
    logger.info(f"CDR processed: {cdr.type.value} | {cdr.id}")
    did = did_pool.get_by_number(cdr.destination_number)
    if did and did.allocated_to:
        await ws_manager.notify(did.allocated_to, "cdr_update", cdr.model_dump())


async def handle_incoming_call(message: IncomingMessage):
    cdr = CallDetailRecord(
        type=CDRType.CALL_INCOMING,
        source_number=message.source,
        destination_number=message.destination,
        session_id=message.call_id,
        raw_payload=message.model_dump_json(),
    )
    await cdr_processor.enqueue(cdr)

    did = did_pool.get_by_number(message.destination)
    if did and did.allocated_to:
        await ws_manager.notify(did.allocated_to, "call_incoming", {
            "from": SMSCodeExtractor.mask_sensitive(message.source),
            "call_id": message.call_id,
        })

    logger.info(f"Call received: {message.source[:5]}*** -> {message.destination}")


async def handle_incoming_sms(message: IncomingMessage):
    code = SMSCodeExtractor.extract(message.text or "")
    masked_content = SMSCodeExtractor.mask_sensitive(message.text or "")

    cdr = CallDetailRecord(
        type=CDRType.SMS_INCOMING,
        source_number=message.source,
        destination_number=message.destination,
        session_id=message.call_id,
        sms_content=masked_content,
        extracted_code=code,
        raw_payload=message.model_dump_json(),
    )
    await cdr_processor.enqueue(cdr)

    did = did_pool.get_by_number(message.destination)
    if did and did.allocated_to:
        await ws_manager.notify(did.allocated_to, "sms_received", {
            "from": SMSCodeExtractor.mask_sensitive(message.source),
            "content": masked_content,
            "code": code,
            "call_id": message.call_id,
        })

    logger.info(f"SMS received: {message.source[:5]}*** -> {message.destination} | Code: {code or 'N/A'}")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
