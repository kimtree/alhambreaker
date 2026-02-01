"""Main ticket availability checker logic."""

import logging
from dataclasses import dataclass, field
from datetime import date

from .browser import AlhambraBrowser, DateAvailability, TicketStatus
from .captcha import CaptchaError, CaptchaSolver
from .config import Settings
from .notifier import NotificationError, TelegramNotifier

__all__ = ["AlhambraChecker", "CheckResult"]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CheckResult:
    """Result of a ticket availability check."""

    dates: list[date]
    results: list[DateAvailability] = field(default_factory=list)
    available_dates: list[DateAvailability] = field(default_factory=list)
    notification_sent: bool = False
    error: str | None = None

    @property
    def is_available(self) -> bool:
        """Check if any date is available."""
        return len(self.available_dates) > 0


class AlhambraChecker:
    """Orchestrates the ticket availability checking process."""

    def __init__(self, settings: Settings):
        """Initialize the checker with settings.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self._captcha_solver = CaptchaSolver(
            settings.captcha_api_key,
            timeout=settings.captcha_timeout,
        )
        self._notifier = TelegramNotifier(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
        )

    async def check_availability(self, dry_run: bool = False) -> CheckResult:
        """Check ticket availability for the target dates.

        Args:
            dry_run: If True, don't send notifications.

        Returns:
            CheckResult with the outcome.
        """
        target_dates = self.settings.target_dates
        dates_str = ", ".join(d.isoformat() for d in target_dates)
        logger.info("Starting availability check for %s", dates_str)

        try:
            async with AlhambraBrowser(
                headless=self.settings.headless,
                timeout=self.settings.browser_timeout,
            ) as browser:
                # Step 1: Navigate to purchase page
                await browser.navigate_to_purchase_page()
                await browser.accept_cookies()

                # Step 2: Solve captcha
                page_url = await browser.get_page_url()
                captcha_token = await self._captcha_solver.solve_recaptcha(
                    site_key=self.settings.recaptcha_site_key,
                    page_url=page_url,
                )

                # Step 3: Inject token and proceed
                await browser.inject_captcha_token(captcha_token)
                await browser.click_go_to_step1()

                # Step 4: Navigate to target month (all dates are in same month)
                await browser.navigate_to_month(target_dates[0])

                # Step 5: Check all dates availability
                results = await browser.check_dates_availability(target_dates)

                # Step 6: Filter available dates
                available_dates = [
                    r for r in results
                    if r.status in (TicketStatus.AVAILABLE, TicketStatus.LAST_TICKETS)
                ]

                # Step 7: Send notification if any available
                notification_sent = False
                if available_dates and not dry_run:
                    await self._send_notification(available_dates)
                    notification_sent = True

                return CheckResult(
                    dates=target_dates,
                    results=results,
                    available_dates=available_dates,
                    notification_sent=notification_sent,
                )

        except CaptchaError as e:
            logger.error("Captcha error: %s", e)
            return CheckResult(
                dates=target_dates,
                error=f"Captcha error: {e}",
            )
        except NotificationError as e:
            logger.error("Notification error: %s", e)
            return CheckResult(
                dates=target_dates,
                error=f"Notification error: {e}",
            )
        except Exception as e:
            logger.exception("Unexpected error during check")
            return CheckResult(
                dates=target_dates,
                error=str(e),
            )

    async def _send_notification(
        self, available_dates: list[DateAvailability]
    ) -> None:
        """Send a Telegram notification for available dates.

        Args:
            available_dates: List of available date information.
        """
        await self._notifier.send_availability_alert(
            available_dates=available_dates,
            ticket_type=self.settings.ticket_type,
        )

    async def test_telegram(self) -> bool:
        """Test Telegram bot connection.

        Returns:
            True if connection is successful.
        """
        return await self._notifier.test_connection()
