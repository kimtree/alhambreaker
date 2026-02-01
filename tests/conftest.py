"""Pytest fixtures and configuration."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from alhambreaker.browser import DateAvailability, TicketStatus
from alhambreaker.config import Settings


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        captcha_api_key="test_captcha_key",
        telegram_bot_token="test_bot_token",
        telegram_chat_id="123456789",
        TARGET_DATES="2026-02-17",
        ticket_type="GENERAL",
        headless=True,
        browser_timeout=30000,
    )


@pytest.fixture
def mock_available_date() -> DateAvailability:
    """Create a mock available date."""
    return DateAvailability(
        date=date(2026, 2, 17),
        status=TicketStatus.AVAILABLE,
        has_link=True,
    )


@pytest.fixture
def mock_unavailable_date() -> DateAvailability:
    """Create a mock unavailable date."""
    return DateAvailability(
        date=date(2026, 2, 17),
        status=TicketStatus.NOT_AVAILABLE,
        has_link=False,
    )


@pytest.fixture
def mock_browser():
    """Create a mock browser."""
    browser = MagicMock()
    browser.__aenter__ = AsyncMock(return_value=browser)
    browser.__aexit__ = AsyncMock(return_value=None)
    browser.navigate_to_purchase_page = AsyncMock()
    browser.accept_cookies = AsyncMock()
    browser.inject_captcha_token = AsyncMock()
    browser.click_go_to_step1 = AsyncMock()
    browser.navigate_to_month = AsyncMock()
    browser.check_date_availability = AsyncMock()
    browser.check_dates_availability = AsyncMock()
    browser.get_page_url = AsyncMock(return_value="https://example.com")
    return browser


@pytest.fixture
def mock_captcha_solver():
    """Create a mock captcha solver."""
    solver = MagicMock()
    solver.solve_recaptcha = AsyncMock(return_value="mock_captcha_token")
    return solver


@pytest.fixture
def mock_notifier():
    """Create a mock notifier."""
    notifier = MagicMock()
    notifier.send_availability_alert = AsyncMock()
    notifier.send_error_alert = AsyncMock()
    notifier.test_connection = AsyncMock(return_value=True)
    return notifier
