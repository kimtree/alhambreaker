"""Tests for configuration module."""

from datetime import date

import pytest

from alhambreaker.config import Settings


class TestSettings:
    """Tests for Settings class."""

    def test_settings_from_env(self, monkeypatch):
        """Test settings can be loaded from environment variables."""
        monkeypatch.setenv("CAPTCHA_API_KEY", "test_key")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        monkeypatch.setenv("TARGET_DATE", "2026-02-17")

        settings = Settings()

        assert settings.captcha_api_key == "test_key"
        assert settings.telegram_bot_token == "test_token"
        assert settings.telegram_chat_id == "12345"
        assert settings.target_date == date(2026, 2, 17)

    def test_settings_defaults(self, monkeypatch):
        """Test default settings values."""
        monkeypatch.setenv("CAPTCHA_API_KEY", "test_key")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        monkeypatch.setenv("TARGET_DATE", "2026-02-17")

        settings = Settings()

        assert settings.ticket_type == "GENERAL"
        assert settings.headless is True
        assert settings.browser_timeout == 30000

    def test_settings_recaptcha_site_key(self, monkeypatch):
        """Test reCAPTCHA site key is set correctly."""
        monkeypatch.setenv("CAPTCHA_API_KEY", "test_key")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        monkeypatch.setenv("TARGET_DATE", "2026-02-17")

        settings = Settings()

        assert settings.recaptcha_site_key == "6LfXS2IUAAAAADr2WUPQDzAnTEbSQzE1Jxh0Zi0a"

    def test_settings_missing_required(self, monkeypatch, tmp_path):
        """Test that missing required settings raise an error."""
        # Clear any existing env vars
        monkeypatch.delenv("CAPTCHA_API_KEY", raising=False)
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        monkeypatch.delenv("TARGET_DATE", raising=False)

        # Change to temp directory to avoid loading .env file
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValueError):  # pydantic ValidationError
            Settings()
