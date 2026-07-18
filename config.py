from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "SMS VoIP Servisi - Virtual Number Receiver"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
