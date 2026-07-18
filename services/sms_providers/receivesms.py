import re
import logging
from datetime import datetime
from typing import Optional
from .provider_base import SMSProvider, IncomingSMS

logger = logging.getLogger(__name__)

COUNTRIES = [
    {"code": "US", "name": "United States", "flag": "🇺🇸"},
    {"code": "GB", "name": "United Kingdom", "flag": "🇬🇧"},
    {"code": "CA", "name": "Canada", "flag": "🇨🇦"},
    {"code": "AU", "name": "Australia", "flag": "🇦🇺"},
    {"code": "DE", "name": "Germany", "flag": "🇩🇪"},
    {"code": "FR", "name": "France", "flag": "🇫🇷"},
    {"code": "IT", "name": "Italy", "flag": "🇮🇹"},
    {"code": "ES", "name": "Spain", "flag": "🇪🇸"},
    {"code": "NL", "name": "Netherlands", "flag": "🇳🇱"},
    {"code": "BR", "name": "Brazil", "flag": "🇧🇷"},
    {"code": "RU", "name": "Russia", "flag": "🇷🇺"},
    {"code": "IN", "name": "India", "flag": "🇮🇳"},
    {"code": "CN", "name": "China", "flag": "🇨🇳"},
    {"code": "JP", "name": "Japan", "flag": "🇯🇵"},
    {"code": "KR", "name": "South Korea", "flag": "🇰🇷"},
    {"code": "TR", "name": "Turkey", "flag": "🇹🇷"},
    {"code": "ID", "name": "Indonesia", "flag": "🇮🇩"},
    {"code": "MX", "name": "Mexico", "flag": "🇲🇽"},
    {"code": "VN", "name": "Vietnam", "flag": "🇻🇳"},
    {"code": "PH", "name": "Philippines", "flag": "🇵🇭"},
    {"code": "SG", "name": "Singapore", "flag": "🇸🇬"},
    {"code": "MY", "name": "Malaysia", "flag": "🇲🇾"},
    {"code": "TH", "name": "Thailand", "flag": "🇹🇭"},
    {"code": "ZA", "name": "South Africa", "flag": "🇿🇦"},
    {"code": "NG", "name": "Nigeria", "flag": "🇳🇬"},
    {"code": "EG", "name": "Egypt", "flag": "🇪🇬"},
    {"code": "SA", "name": "Saudi Arabia", "flag": "🇸🇦"},
    {"code": "AE", "name": "UAE", "flag": "🇦🇪"},
    {"code": "IL", "name": "Israel", "flag": "🇮🇱"},
    {"code": "SE", "name": "Sweden", "flag": "🇸🇪"},
    {"code": "NO", "name": "Norway", "flag": "🇳🇴"},
    {"code": "DK", "name": "Denmark", "flag": "🇩🇰"},
    {"code": "FI", "name": "Finland", "flag": "🇫🇮"},
    {"code": "PL", "name": "Poland", "flag": "🇵🇱"},
    {"code": "UA", "name": "Ukraine", "flag": "🇺🇦"},
    {"code": "RO", "name": "Romania", "flag": "🇷🇴"},
    {"code": "CZ", "name": "Czech Republic", "flag": "🇨🇿"},
    {"code": "PT", "name": "Portugal", "flag": "🇵🇹"},
    {"code": "GR", "name": "Greece", "flag": "🇬🇷"},
    {"code": "IE", "name": "Ireland", "flag": "🇮🇪"},
    {"code": "NZ", "name": "New Zealand", "flag": "🇳🇿"},
    {"code": "HK", "name": "Hong Kong", "flag": "🇭🇰"},
    {"code": "TW", "name": "Taiwan", "flag": "🇹🇼"},
    {"code": "PK", "name": "Pakistan", "flag": "🇵🇰"},
    {"code": "BD", "name": "Bangladesh", "flag": "🇧🇩"},
    {"code": "KE", "name": "Kenya", "flag": "🇰🇪"},
    {"code": "CO", "name": "Colombia", "flag": "🇨🇴"},
    {"code": "AR", "name": "Argentina", "flag": "🇦🇷"},
    {"code": "CL", "name": "Chile", "flag": "🇨🇱"},
    {"code": "PE", "name": "Peru", "flag": "🇵🇪"},
]


class ReceiveSMSMeProvider(SMSProvider):

    API_BASE = "https://receivesms.me/api/v1"

    def __init__(self):
        self._cache: dict[str, list[IncomingSMS]] = {}

    @property
    def name(self) -> str:
        return "receivesms.me"

    async def is_available(self) -> bool:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.API_BASE}/countries", timeout=10) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def get_supported_countries(self) -> list[dict]:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.API_BASE}/countries", timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            return data
            return COUNTRIES
        except Exception:
            logger.warning("receivesms.me API unreachable, using fallback country list")
            return COUNTRIES

    async def get_numbers(self, country_code: str) -> list[str]:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.API_BASE}/numbers",
                    params={"country": country_code},
                    timeout=15,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            return data[:5]
            return self._fallback_numbers(country_code)
        except Exception:
            logger.warning(f"Failed to fetch numbers for {country_code}, using fallback")
            return self._fallback_numbers(country_code)

    async def get_messages(self, number: str) -> list[IncomingSMS]:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.API_BASE}/messages",
                    params={"number": number},
                    timeout=15,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            results = []
                            for msg in data:
                                text = msg.get("text", msg.get("message", ""))
                                results.append(IncomingSMS(
                                    number=number,
                                    sender=msg.get("from", msg.get("sender", "unknown")),
                                    text=text,
                                    received_at=datetime.utcnow(),
                                    provider=self.name,
                                ))
                            self._cache[number] = results
                            return results
            return self._cache.get(number, [])
        except Exception:
            return self._cache.get(number, [])

    def _fallback_numbers(self, country_code: str) -> list[str]:
        prefixes = {
            "US": "+1", "GB": "+44", "CA": "+1", "AU": "+61",
            "DE": "+49", "FR": "+33", "IT": "+39", "ES": "+34",
            "TR": "+90", "BR": "+55", "IN": "+91", "RU": "+7",
            "JP": "+81", "KR": "+82", "CN": "+86", "NL": "+31",
            "SG": "+65", "MY": "+60", "TH": "+66", "VN": "+84",
            "PH": "+63", "ID": "+62", "MX": "+52", "ZA": "+27",
        }
        prefix = prefixes.get(country_code, "+1")
        return [f"{prefix}555{hash(country_code) % 1000000:06d}"]
