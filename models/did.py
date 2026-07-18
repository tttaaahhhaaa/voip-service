from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class DIDStatus(str, Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    BUSY = "busy"
    MAINTENANCE = "maintenance"


class DIDNumber(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: str
    country_code: str = "90"
    status: DIDStatus = DIDStatus.AVAILABLE
    allocated_to: Optional[str] = None
    allocated_at: Optional[datetime] = None
    mask: Optional[str] = None
