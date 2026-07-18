import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from config import Settings
from services.sms_provider_manager import SMSProviderManager
from services.sms_parser import SMSCodeExtractor
from services.local_storage import LocalStorage
from services.sms_providers import IncomingSMS
from routers.ws import manager as ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = Settings()
sms_manager = SMSProviderManager()
local_db = LocalStorage()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Messages stored at: {local_db.db_path}")

    await sms_manager.init_defaults()

    sms_manager.on_new_message(on_sms_received)
    sms_manager.start_polling(interval=5)

    import routers.sms_provider as sms_router
    sms_router.provider_mgr = sms_manager
    sms_router.local_db = local_db

    logger.info(f"SMS Providers: {sms_manager.get_providers()}, Active: {sms_manager.provider_name}")
    yield

    await sms_manager.stop_polling()
    logger.info("Application shutdown complete")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

from routers.sms_provider import router as sms_router
from routers.ws import router as ws_router

app.include_router(sms_router)
app.include_router(ws_router)


async def on_sms_received(msg: IncomingSMS):
    code = SMSCodeExtractor.extract(msg.text) or msg.code or ""
    masked = SMSCodeExtractor.mask_sensitive(msg.text)

    local_db.save_message(
        number=msg.number,
        sender=msg.sender,
        text=masked,
        code=code,
        provider=msg.provider,
    )

    logger.info(f"SMS from {msg.sender}: {masked[:60]} | Code: {code or 'N/A'}")

    await ws_manager.broadcast("sms_received", {
        "from": msg.sender,
        "to": msg.number,
        "content": masked,
        "code": code,
        "provider": msg.provider,
    })


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(html)


@app.get("/api/info")
async def app_info():
    return {
        "app": settings.APP_NAME,
        "providers": sms_manager.get_providers(),
        "active_provider": sms_manager.provider_name,
        "db_path": local_db.db_path,
        "total_messages": len(local_db.get_messages(limit=99999)),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
