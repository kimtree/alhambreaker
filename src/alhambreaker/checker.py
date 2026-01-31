"""Main ticket availability checker logic."""

import logging
from dataclasses import dataclass
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

    date: date
    status: TicketStatus
    is_available: bool
    notification_sent: bool
    error: str | None = None


class AlhambraChecker:
    """Orchestrates the ticket availability checking process."""

    def __init__(self, settings: Settings):
        """Initialize the checker with settings.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self._captcha_solver = CaptchaSolver(settings.captcha_api_key)
        self._notifier = TelegramNotifier(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
        )

    async def check_availability(self, dry_run: bool = False) -> CheckResult:
        """Check ticket availability for the target date.

        Args:
            dry_run: If True, don't send notifications.

        Returns:
            CheckResult with the outcome.
        """
        target_date = self.settings.target_date
        logger.info("Starting availability check for %s", target_date)

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

                # Step 4: Navigate to target month
                await browser.navigate_to_month(target_date)

                # Step 5: Check date availability
                availability = await browser.check_date_availability(target_date)

                # Step 6: Send notification if available
                notification_sent = False
                if self._should_notify(availability) and not dry_run:
                    await self._send_notification(availability)
                    notification_sent = True

                return CheckResult(
                    date=target_date,
                    status=availability.status,
                    is_available=availability.status in (
                        TicketStatus.AVAILABLE,
                        TicketStatus.LAST_TICKETS,
                    ),
                    notification_sent=notification_sent,
                )

        except CaptchaError as e:
            logger.error("Captcha error: %s", e)
            return CheckResult(
                date=target_date,
                status=TicketStatus.UNKNOWN,
                is_available=False,
                notification_sent=False,
                error=f"Captcha error: {e}",
            )
        except NotificationError as e:
            logger.error("Notification error: %s", e)
            return CheckResult(
                date=target_date,
                status=TicketStatus.UNKNOWN,
                is_available=False,
                notification_sent=False,
                error=f"Notification error: {e}",
            )
        except Exception as e:
            logger.exception("Unexpected error during check")
            return CheckResult(
                date=target_date,
                status=TicketStatus.UNKNOWN,
                is_available=False,
                notification_sent=False,
                error=str(e),
            )

    def _should_notify(self, availability: DateAvailability) -> bool:
        """Determine if a notification should be sent.

        Args:
            availability: The date availability information.

        Returns:
            True if notification should be sent.
        """
        return availability.status in (
            TicketStatus.AVAILABLE,
            TicketStatus.LAST_TICKETS,
        )

    async def _send_notification(self, availability: DateAvailability) -> None:
        """Send a Telegram notification for availability.

        Args:
            availability: The date availability information.
        """
        status_text = (
            "Available" if availability.status == TicketStatus.AVAILABLE
            else "Last Tickets!"
        )

        await self._notifier.send_availability_alert(
            target_date=availability.date,
            status=status_text,
            ticket_type=self.settings.ticket_type,
        )

    async def test_telegram(self) -> bool:
        """Test Telegram bot connection.

        Returns:
            True if connection is successful.
        """
        return await self._notifier.test_connection()
