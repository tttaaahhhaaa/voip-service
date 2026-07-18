import random
from datetime import datetime
from typing import Optional
from .provider_base import SMSProvider, IncomingSMS

SAMPLE_COUNTRIES = [
    {"code": "TR", "name": "Turkey", "flag": "🇹🇷"},
    {"code": "US", "name": "United States", "flag": "🇺🇸"},
    {"code": "GB", "name": "United Kingdom", "flag": "🇬🇧"},
    {"code": "DE", "name": "Germany", "flag": "🇩🇪"},
    {"code": "FR", "name": "France", "flag": "🇫🇷"},
]


class SimulationProvider(SMSProvider):

    def __init__(self):
        self._messages: dict[str, list[IncomingSMS]] = {}
        self._counter = 0

    @property
    def name(self) -> str:
        return "simulation"

    async def is_available(self) -> bool:
        return True

    async def get_supported_countries(self) -> list[dict]:
        return SAMPLE_COUNTRIES

    async def get_numbers(self, country_code: str) -> list[str]:
        prefixes = {"TR": "+90555", "US": "+1555", "GB": "+447555", "DE": "+491555", "FR": "+336555"}
        prefix = prefixes.get(country_code, "+1555")
        return [f"{prefix}{1000 + i:04d}" for i in range(3)]

    async def get_messages(self, number: str) -> list[IncomingSMS]:
        self._counter += 1
        if self._counter < 3:
            return []
        self._counter = 0
        sim_code = f"{random.randint(100000, 999999)}"
        msg = IncomingSMS(
            number=number,
            sender="WhatsApp",
            text=f"Your WhatsApp verification code is: {sim_code}. Do not share this code.",
            code=sim_code,
            received_at=datetime.utcnow(),
            provider=self.name,
        )
        self._messages.setdefault(number, []).append(msg)
        return [msg]
