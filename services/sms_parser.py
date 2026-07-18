import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SMSCodeExtractor:

    PATTERNS = [
        r'(?:kod|code|pin|otp|sifre|password|doğrulama|verification|şifre|login|giriş)[:\s]*(\d{4,8})',
        r'(\d{4,8})\s*(?:kod|code|pin|otp|sifre|doğrulama|verification)',
        r'(?:one-time|tek\s*kullanımlık|security|güvenlik)[:\s]*(\d{4,8})',
        r'(?:şifre|parola|password|code|token)[:\s]*(\d{4,8})',
        r'(?:WhatsApp|Telegram|Google|Facebook|Instagram|Twitter|Microsoft|Apple|Amazon|Netflix|Spotify|Discord|TikTok|Snapchat)\s*(?:kod|code|pin|onay|doğrulama)[:\s]*(\d{4,8})',
        r'(\d{4,8})\s*(?:is your|kodunuz|code|pin|şifre)',
        r'\b(\d{6})\b',
        r'\b(\d{4})\b',
    ]

    @classmethod
    def extract(cls, text: str) -> Optional[str]:
        if not text:
            return None
        for pattern in cls.PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def mask_sensitive(text: str) -> str:
        text = re.sub(r'\b(\d{3})\d{4}(\d{4})\b', r'\1****\2', text)
        text = re.sub(r'([\w.+-]+)@([\w-]+\.)+[\w-]+', '***@***', text)
        return text
