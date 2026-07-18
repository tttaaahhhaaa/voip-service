import re
from typing import Optional


class SMSCodeExtractor:

    PATTERNS = [
        r'(?:kod|code|pin|otp|sifre|password|doğrulama|verification|şifre)[:\s]*(\d{6})',
        r'(\d{6})\s*(?:kod|code|pin|otp|sifre|doğrulama|verification)',
        r'(?:one-time|tek\s*kullanımlık)[:\s]*(\d{6})',
        r'(?:şifre|parola|password|code)[:\s]*(\d{6})',
        r'\b(\d{6})\b',
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
