"""Configuration management using pydantic-settings."""

from datetime import date
from functools import cached_property, lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "get_settings"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 2Captcha
    captcha_api_key: str = Field(description="2Captcha API key")

    # Telegram
    telegram_bot_token: str = Field(description="Telegram bot token")
    telegram_chat_id: str = Field(description="Telegram chat ID")

    # Monitoring - stored as string, parsed via property
    target_dates_str: str = Field(
        alias="TARGET_DATES",
        description="Target dates to monitor (comma-separated YYYY-MM-DD)",
    )
    ticket_type: str = Field(default="GENERAL", description="Ticket type")

    @cached_property
    def target_dates(self) -> list[date]:
        """Parse target dates from string."""
        return [date.fromisoformat(d.strip()) for d in self.target_dates_str.split(",")]

    @model_validator(mode="after")
    def validate_same_month(self) -> "Settings":
        """Ensure all target dates are in the same month."""
        dates = self.target_dates
        if len(dates) > 1:
            first = dates[0]
            for d in dates[1:]:
                if d.year != first.year or d.month != first.month:
                    raise ValueError("All target dates must be in the same month")
        return self

    # Browser
    headless: bool = Field(default=True, description="Run browser in headless mode")
    browser_timeout: int = Field(default=30000, description="Browser timeout in ms")

    # Site configuration (constants)
    site_url: str = Field(
        default="https://compratickets.alhambra-patronato.es/reservarEntradas.aspx",
        description="Ticket purchase page URL",
    )
    recaptcha_site_key: str = Field(
        default="6LfXS2IUAAAAADr2WUPQDzAnTEbSQzE1Jxh0Zi0a",
        description="reCAPTCHA site key",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
