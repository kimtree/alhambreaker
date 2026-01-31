"""Tests for main checker module."""

from datetime import date

import pytest

from alhambreaker.browser import DateAvailability, TicketStatus
from alhambreaker.checker import AlhambraChecker, CheckResult


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_check_result_available(self):
        """Test check result for available date."""
        result = CheckResult(
            date=date(2026, 2, 17),
            status=TicketStatus.AVAILABLE,
            is_available=True,
            notification_sent=True,
        )

        assert result.is_available is True
        assert result.notification_sent is True
        assert result.error is None

    def test_check_result_not_available(self):
        """Test check result for unavailable date."""
        result = CheckResult(
            date=date(2026, 2, 17),
            status=TicketStatus.NOT_AVAILABLE,
            is_available=False,
            notification_sent=False,
        )

        assert result.is_available is False
        assert result.notification_sent is False

    def test_check_result_with_error(self):
        """Test check result with error."""
        result = CheckResult(
            date=date(2026, 2, 17),
            status=TicketStatus.UNKNOWN,
            is_available=False,
            notification_sent=False,
            error="Connection failed",
        )

        assert result.error == "Connection failed"


class TestAlhambraChecker:
    """Tests for AlhambraChecker class."""

    @pytest.mark.asyncio
    async def test_check_availability_available(
        self,
        mock_settings,
        mock_available_date,
        mocker,
    ):
        """Test checking availability when tickets are available."""
        # Mock browser
        mock_browser = mocker.MagicMock()
        mock_browser.__aenter__ = mocker.AsyncMock(return_value=mock_browser)
        mock_browser.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_browser.navigate_to_purchase_page = mocker.AsyncMock()
        mock_browser.accept_cookies = mocker.AsyncMock()
        mock_browser.inject_captcha_token = mocker.AsyncMock()
        mock_browser.click_go_to_step1 = mocker.AsyncMock()
        mock_browser.navigate_to_month = mocker.AsyncMock()
        mock_browser.check_date_availability = mocker.AsyncMock(
            return_value=mock_available_date
        )
        mock_browser.get_page_url = mocker.AsyncMock(return_value="https://example.com")

        mocker.patch(
            "alhambreaker.checker.AlhambraBrowser",
            return_value=mock_browser,
        )

        # Mock captcha solver
        mock_solver = mocker.MagicMock()
        mock_solver.solve_recaptcha = mocker.AsyncMock(return_value="mock_token")
        mocker.patch(
            "alhambreaker.checker.CaptchaSolver",
            return_value=mock_solver,
        )

        # Mock notifier
        mock_notifier = mocker.MagicMock()
        mock_notifier.send_availability_alert = mocker.AsyncMock()
        mocker.patch(
            "alhambreaker.checker.TelegramNotifier",
            return_value=mock_notifier,
        )

        checker = AlhambraChecker(mock_settings)
        result = await checker.check_availability()

        assert result.is_available is True
        assert result.status == TicketStatus.AVAILABLE
        assert result.notification_sent is True
        mock_notifier.send_availability_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_availability_not_available(
        self,
        mock_settings,
        mock_unavailable_date,
        mocker,
    ):
        """Test checking availability when tickets are not available."""
        # Mock browser
        mock_browser = mocker.MagicMock()
        mock_browser.__aenter__ = mocker.AsyncMock(return_value=mock_browser)
        mock_browser.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_browser.navigate_to_purchase_page = mocker.AsyncMock()
        mock_browser.accept_cookies = mocker.AsyncMock()
        mock_browser.inject_captcha_token = mocker.AsyncMock()
        mock_browser.click_go_to_step1 = mocker.AsyncMock()
        mock_browser.navigate_to_month = mocker.AsyncMock()
        mock_browser.check_date_availability = mocker.AsyncMock(
            return_value=mock_unavailable_date
        )
        mock_browser.get_page_url = mocker.AsyncMock(return_value="https://example.com")

        mocker.patch(
            "alhambreaker.checker.AlhambraBrowser",
            return_value=mock_browser,
        )

        # Mock captcha solver
        mock_solver = mocker.MagicMock()
        mock_solver.solve_recaptcha = mocker.AsyncMock(return_value="mock_token")
        mocker.patch(
            "alhambreaker.checker.CaptchaSolver",
            return_value=mock_solver,
        )

        # Mock notifier
        mock_notifier = mocker.MagicMock()
        mock_notifier.send_availability_alert = mocker.AsyncMock()
        mocker.patch(
            "alhambreaker.checker.TelegramNotifier",
            return_value=mock_notifier,
        )

        checker = AlhambraChecker(mock_settings)
        result = await checker.check_availability()

        assert result.is_available is False
        assert result.status == TicketStatus.NOT_AVAILABLE
        assert result.notification_sent is False
        mock_notifier.send_availability_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_availability_dry_run(
        self,
        mock_settings,
        mock_available_date,
        mocker,
    ):
        """Test dry run mode doesn't send notifications."""
        # Mock browser
        mock_browser = mocker.MagicMock()
        mock_browser.__aenter__ = mocker.AsyncMock(return_value=mock_browser)
        mock_browser.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_browser.navigate_to_purchase_page = mocker.AsyncMock()
        mock_browser.accept_cookies = mocker.AsyncMock()
        mock_browser.inject_captcha_token = mocker.AsyncMock()
        mock_browser.click_go_to_step1 = mocker.AsyncMock()
        mock_browser.navigate_to_month = mocker.AsyncMock()
        mock_browser.check_date_availability = mocker.AsyncMock(
            return_value=mock_available_date
        )
        mock_browser.get_page_url = mocker.AsyncMock(return_value="https://example.com")

        mocker.patch(
            "alhambreaker.checker.AlhambraBrowser",
            return_value=mock_browser,
        )

        # Mock captcha solver
        mock_solver = mocker.MagicMock()
        mock_solver.solve_recaptcha = mocker.AsyncMock(return_value="mock_token")
        mocker.patch(
            "alhambreaker.checker.CaptchaSolver",
            return_value=mock_solver,
        )

        # Mock notifier
        mock_notifier = mocker.MagicMock()
        mock_notifier.send_availability_alert = mocker.AsyncMock()
        mocker.patch(
            "alhambreaker.checker.TelegramNotifier",
            return_value=mock_notifier,
        )

        checker = AlhambraChecker(mock_settings)
        result = await checker.check_availability(dry_run=True)

        assert result.is_available is True
        assert result.notification_sent is False
        mock_notifier.send_availability_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_notify_available(self, mock_settings):
        """Test _should_notify returns True for available status."""
        checker = AlhambraChecker(mock_settings)

        availability = DateAvailability(
            date=date(2026, 2, 17),
            status=TicketStatus.AVAILABLE,
            has_link=True,
        )

        assert checker._should_notify(availability) is True

    @pytest.mark.asyncio
    async def test_should_notify_last_tickets(self, mock_settings):
        """Test _should_notify returns True for last tickets status."""
        checker = AlhambraChecker(mock_settings)

        availability = DateAvailability(
            date=date(2026, 2, 17),
            status=TicketStatus.LAST_TICKETS,
            has_link=True,
        )

        assert checker._should_notify(availability) is True

    @pytest.mark.asyncio
    async def test_should_notify_not_available(self, mock_settings):
        """Test _should_notify returns False for not available status."""
        checker = AlhambraChecker(mock_settings)

        availability = DateAvailability(
            date=date(2026, 2, 17),
            status=TicketStatus.NOT_AVAILABLE,
            has_link=False,
        )

        assert checker._should_notify(availability) is False
