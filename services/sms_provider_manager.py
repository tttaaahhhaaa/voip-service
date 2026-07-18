import asyncio
import logging
from typing import Optional
from .sms_providers import SMSProvider, IncomingSMS, ReceiveSMSMeProvider, SimulationProvider

logger = logging.getLogger(__name__)


class SMSProviderManager:

    def __init__(self):
        self._providers: dict[str, SMSProvider] = {}
        self._active_provider: Optional[str] = None
        self._selected_number: Optional[str] = None
        self._message_history: list[IncomingSMS] = []
        self._poll_task: Optional[asyncio.Task] = None
        self._on_message = None

    def register_provider(self, provider: SMSProvider):
        self._providers[provider.name] = provider
        logger.info(f"Registered SMS provider: {provider.name}")

    async def init_defaults(self):
        self.register_provider(ReceiveSMSMeProvider())
        self.register_provider(SimulationProvider())
        for p in self._providers.values():
            if await p.is_available():
                self._active_provider = p.name
                logger.info(f"Active provider: {p.name}")
                return
        self._active_provider = "simulation"
        logger.info("No provider available, using simulation")

    @property
    def active_provider(self) -> Optional[SMSProvider]:
        if self._active_provider:
            return self._providers.get(self._active_provider)
        return None

    @property
    def provider_name(self) -> str:
        return self._active_provider or "none"

    def set_provider(self, name: str) -> bool:
        if name in self._providers:
            self._active_provider = name
            logger.info(f"Switched to provider: {name}")
            return True
        return False

    def get_providers(self) -> list[str]:
        return list(self._providers.keys())

    async def get_countries(self) -> list[dict]:
        p = self.active_provider
        if p:
            return await p.get_supported_countries()
        return []

    async def get_numbers(self, country_code: str) -> list[str]:
        p = self.active_provider
        if p:
            nums = await p.get_numbers(country_code)
            return nums
        return []

    def select_number(self, number: str):
        self._selected_number = number
        logger.info(f"Selected number: {number}")

    def get_selected_number(self) -> Optional[str]:
        return self._selected_number

    def get_message_history(self) -> list[IncomingSMS]:
        return list(self._message_history)

    def on_new_message(self, callback):
        self._on_message = callback

    async def poll_messages(self, interval: int = 5):
        while True:
            try:
                if self._active_provider and self._selected_number:
                    p = self.active_provider
                    if p:
                        msgs = await p.get_messages(self._selected_number)
                        for msg in msgs:
                            if msg not in self._message_history:
                                self._message_history.append(msg)
                                if self._on_message:
                                    await self._on_message(msg)
            except Exception as e:
                logger.warning(f"Poll error: {e}")
            await asyncio.sleep(interval)

    def start_polling(self, interval: int = 5):
        if self._poll_task is None:
            self._poll_task = asyncio.create_task(self.poll_messages(interval))
            logger.info("SMS polling started")

    async def stop_polling(self):
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
