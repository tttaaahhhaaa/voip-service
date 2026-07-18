from fastapi import APIRouter, HTTPException
from services.did_pool import DIDPool
from models import DIDNumber

router = APIRouter(prefix="/api/did", tags=["DID Management"])

did_pool: DIDPool = None


@router.get("/", response_model=list[DIDNumber])
async def list_available():
    return did_pool.list_available()


@router.post("/allocate")
async def allocate_number(user_id: str):
    did = did_pool.allocate(user_id)
    if not did:
        raise HTTPException(status_code=404, detail="No available DID numbers")
    return did


@router.post("/release/{number}")
async def release_number(number: str):
    if not did_pool.release(number):
        raise HTTPException(status_code=404, detail="DID not found or not allocated")
    return {"status": "released", "number": number}


@router.get("/my/{user_id}")
async def get_my_number(user_id: str):
    did = did_pool.get_allocated(user_id)
    if not did:
        raise HTTPException(status_code=404, detail="No number allocated")
    return did
