from fastapi import APIRouter, HTTPException, Query
from services.sms_provider_manager import SMSProviderManager
from services.sms_parser import SMSCodeExtractor
from services.local_storage import LocalStorage

router = APIRouter(prefix="/api/sms", tags=["SMS Provider"])

provider_mgr: SMSProviderManager = None
local_db: LocalStorage = None


@router.get("/countries")
async def list_countries():
    countries = await provider_mgr.get_countries()
    if not countries:
        raise HTTPException(status_code=503, detail="No provider available")
    return countries


@router.get("/numbers")
async def list_numbers(country: str = Query(default="US")):
    nums = await provider_mgr.get_numbers(country)
    if not nums:
        raise HTTPException(status_code=404, detail="No numbers available for this country")
    return {"country": country, "numbers": nums}


@router.post("/select")
async def select_number(number: str = Query(...)):
    provider_mgr.select_number(number)
    local_db.set_setting("last_number", number)
    return {"status": "selected", "number": number}


@router.get("/selected")
async def get_selected():
    num = provider_mgr.get_selected_number()
    if not num:
        num = local_db.get_setting("last_number", "")
        if num:
            provider_mgr.select_number(num)
    if not num:
        raise HTTPException(status_code=404, detail="No number selected")
    return {"number": num}


@router.get("/messages")
async def get_messages():
    msgs = local_db.get_messages(limit=200)
    return msgs


@router.post("/messages/clear")
async def clear_messages():
    local_db.clear_messages()
    return {"status": "cleared"}


@router.get("/providers")
async def list_providers():
    return {"providers": provider_mgr.get_providers(), "active": provider_mgr.provider_name}


@router.post("/provider")
async def set_provider(name: str = Query(...)):
    if provider_mgr.set_provider(name):
        return {"status": "switched", "provider": name}
    raise HTTPException(status_code=404, detail="Provider not found")


@router.get("/extract")
async def extract_code(text: str = Query(...)):
    code = SMSCodeExtractor.extract(text)
    return {"code": code}
