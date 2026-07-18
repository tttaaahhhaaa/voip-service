from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Sanal VoIP ve Cağrı Dağıtım Servisi"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SIP_WEBHOOK_SECRET: str = ""
    DID_POOL_SIZE: int = 50
    DID_ALLOCATION_TIMEOUT_MINUTES: int = 30
    MASK_PHONE_NUMBERS: bool = True
    CDR_RETENTION_DAYS: int = 365
    REDIS_URL: str | None = None

    class Config:
        env_file = ".env"
