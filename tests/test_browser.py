"""Tests for browser automation module."""

from datetime import date

import pytest

from alhambreaker.browser import AlhambraBrowser, DateAvailability, TicketStatus


class TestTicketStatus:
    """Tests for TicketStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert TicketStatus.AVAILABLE.value == "available"
        assert TicketStatus.NOT_AVAILABLE.value == "not_available"
        assert TicketStatus.LAST_TICKETS.value == "last_tickets"
        assert TicketStatus.UNKNOWN.value == "unknown"


class TestDateAvailability:
    """Tests for DateAvailability dataclass."""

    def test_available_date(self):
        """Test available date creation."""
        availability = DateAvailability(
            date=date(2026, 2, 17),
            status=TicketStatus.AVAILABLE,
            has_link=True,
        )

        assert availability.date == date(2026, 2, 17)
        assert availability.status == TicketStatus.AVAILABLE
        assert availability.has_link is True

    def test_unavailable_date(self):
        """Test unavailable date creation."""
        availability = DateAvailability(
            date=date(2026, 2, 17),
            status=TicketStatus.NOT_AVAILABLE,
            has_link=False,
        )

        assert availability.has_link is False
        assert availability.status == TicketStatus.NOT_AVAILABLE


class TestAlhambraBrowser:
    """Tests for AlhambraBrowser class."""

    def test_init_defaults(self):
        """Test browser initialization with defaults."""
        browser = AlhambraBrowser()

        assert browser.headless is True
        assert browser.timeout == 30000

    def test_init_custom(self):
        """Test browser initialization with custom values."""
        browser = AlhambraBrowser(headless=False, timeout=60000)

        assert browser.headless is False
        assert browser.timeout == 60000

    def test_purchase_url(self):
        """Test purchase URL is correct."""
        expected_params = [
            "opc=142",
            "gid=432",
            "lg=en-GB",
            "ca=0",
            "m=GENERAL",
        ]

        for param in expected_params:
            assert param in AlhambraBrowser.PURCHASE_URL

    @pytest.mark.asyncio
    async def test_context_manager(self, mocker):
        """Test browser can be used as async context manager."""
        mock_playwright = mocker.MagicMock()
        mock_browser_instance = mocker.MagicMock()
        mock_page = mocker.MagicMock()

        mock_playwright.start = mocker.AsyncMock(return_value=mock_playwright)
        mock_playwright.stop = mocker.AsyncMock()
        mock_playwright.chromium.launch = mocker.AsyncMock(
            return_value=mock_browser_instance
        )
        mock_browser_instance.new_page = mocker.AsyncMock(return_value=mock_page)
        mock_browser_instance.close = mocker.AsyncMock()
        mock_page.set_default_timeout = mocker.MagicMock()

        mocker.patch(
            "alhambreaker.browser.async_playwright",
            return_value=mock_playwright,
        )

        async with AlhambraBrowser() as browser:
            assert browser._page is mock_page

        mock_browser_instance.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
