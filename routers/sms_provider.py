from fastapi import APIRouter, HTTPException, Query
from services.sms_provider_manager import SMSProviderManager
from services.sms_parser import SMSCodeExtractor

router = APIRouter(prefix="/api/sms", tags=["SMS Provider"])

provider_mgr: SMSProviderManager = None


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
    return {"status": "selected", "number": number}


@router.get("/selected")
async def get_selected():
    num = provider_mgr.get_selected_number()
    if not num:
        raise HTTPException(status_code=404, detail="No number selected")
    return {"number": num}


@router.get("/messages")
async def get_messages():
    msgs = provider_mgr.get_message_history()
    result = []
    for m in msgs:
        result.append({
            "number": m.number,
            "sender": m.sender,
            "text": m.text,
            "code": SMSCodeExtractor.extract(m.text),
            "code_only": m.code,
            "received_at": m.received_at.isoformat() if m.received_at else "",
            "provider": m.provider,
        })
    return result


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
