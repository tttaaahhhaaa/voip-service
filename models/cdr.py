from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class CDRType(str, Enum):
    CALL_INCOMING = "call_incoming"
    SMS_INCOMING = "sms_incoming"
    CALL_OUTGOING = "call_outgoing"


class CallDetailRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: CDRType
    source_number: str
    destination_number: str
    session_id: Optional[str] = None
    duration_seconds: Optional[int] = None
    sms_content: Optional[str] = None
    extracted_code: Optional[str] = None
    raw_payload: Optional[str] = None
    received_at: datetime = Field(default_factory=datetime.utcnow)
