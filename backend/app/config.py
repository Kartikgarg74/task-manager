from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    app_timezone: str = "Asia/Kolkata"

    web_auth_secret: str
    web_auth_email: str
    web_auth_password_hash: str

    notify_email: str
    resend_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
