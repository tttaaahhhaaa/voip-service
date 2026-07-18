from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class IncomingSMS:
    number: str
    sender: str
    text: str
    code: Optional[str] = None
    received_at: datetime = datetime.utcnow()
    provider: str = ""


class SMSProvider(ABC):

    @abstractmethod
    async def get_supported_countries(self) -> list[dict]:
        pass

    @abstractmethod
    async def get_numbers(self, country_code: str) -> list[str]:
        pass

    @abstractmethod
    async def get_messages(self, number: str) -> list[IncomingSMS]:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
