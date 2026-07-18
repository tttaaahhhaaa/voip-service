import logging
from datetime import datetime, timedelta
from typing import Optional
from models import DIDNumber, DIDStatus

logger = logging.getLogger(__name__)


class DIDPool:

    def __init__(self, default_timeout_minutes: int = 30):
        self._numbers: dict[str, DIDNumber] = {}
        self._timeout_minutes = default_timeout_minutes

    def load_pool(self, numbers: list[str], country_code: str = "90"):
        for num in numbers:
            did = DIDNumber(
                number=num,
                country_code=country_code,
                mask=self._mask_number(num),
            )
            self._numbers[num] = did
        logger.info(f"Loaded {len(numbers)} DIDs into pool")

    def list_available(self) -> list[DIDNumber]:
        return [
            d for d in self._numbers.values()
            if d.status == DIDStatus.AVAILABLE
        ]

    def allocate(self, user_id: str) -> Optional[DIDNumber]:
        for did in self._numbers.values():
            if did.status == DIDStatus.AVAILABLE:
                did.status = DIDStatus.ALLOCATED
                did.allocated_to = user_id
                did.allocated_at = datetime.utcnow()
                logger.info(f"DID {did.mask} allocated to {user_id}")
                return did
        return None

    def release(self, number: str) -> bool:
        did = self._numbers.get(number)
        if did and did.status == DIDStatus.ALLOCATED:
            did.status = DIDStatus.AVAILABLE
            did.allocated_to = None
            did.allocated_at = None
            return True
        return False

    def release_by_user(self, user_id: str):
        released = []
        for did in self._numbers.values():
            if did.allocated_to == user_id:
                self.release(did.number)
                released.append(did)
        return released

    def get_by_number(self, number: str) -> Optional[DIDNumber]:
        return self._numbers.get(number)

    def get_allocated(self, user_id: str) -> Optional[DIDNumber]:
        for did in self._numbers.values():
            if did.allocated_to == user_id:
                return did
        return None

    def release_expired(self):
        now = datetime.utcnow()
        released = []
        for did in self._numbers.values():
            if (did.status == DIDStatus.ALLOCATED and did.allocated_at and
                    (now - did.allocated_at) > timedelta(minutes=self._timeout_minutes)):
                self.release(did.number)
                released.append(did)
        return released

    @staticmethod
    def _mask_number(number: str) -> str:
        if len(number) >= 6:
            return number[:3] + "****" + number[-2:]
        return number
