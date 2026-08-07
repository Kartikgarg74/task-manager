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
    # Resend's shared sandbox sender — sends successfully with zero setup.
    # Override once you verify your own domain with Resend.
    notify_from_email: str = "Task Manager <onboarding@resend.dev>"

    # Shared secret for the external cron trigger (GitHub Actions) — a third
    # auth mechanism alongside device tokens and the web JWT, since neither
    # of those fit "a scheduled workflow calling an endpoint."
    internal_cron_secret: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
