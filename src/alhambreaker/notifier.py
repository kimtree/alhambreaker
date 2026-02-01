"""Telegram notification service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from .browser import DateAvailability

__all__ = ["TelegramNotifier", "NotificationError"]

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org"


class NotificationError(Exception):
    """Exception raised when notification fails."""


class TelegramNotifier:
    """Sends notifications via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        """Initialize the notifier.

        Args:
            bot_token: Telegram bot token.
            chat_id: Target chat ID.
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._api_base = f"{TELEGRAM_API_URL}/bot{bot_token}"

    async def send_availability_alert(
        self,
        available_dates: list[DateAvailability],
        ticket_type: str = "GENERAL",
    ) -> None:
        """Send an availability alert message for multiple dates.

        Args:
            available_dates: List of available date information.
            ticket_type: Type of ticket.

        Raises:
            NotificationError: If sending fails.
        """
        from .browser import TicketStatus

        purchase_url = (
            "https://compratickets.alhambra-patronato.es/reservarEntradas.aspx"
            "?opc=142&gid=432&lg=en-GB&ca=0&m=GENERAL"
        )

        # Format each available date
        dates_lines = []
        for avail in available_dates:
            status_text = (
                "Available" if avail.status == TicketStatus.AVAILABLE
                else "Last Tickets!"
            )
            dates_lines.append(
                f"  • {avail.date.strftime('%Y-%m-%d')} - *{status_text}*"
            )

        dates_text = "\n".join(dates_lines)
        message = (
            f"🎫 *Alhambra Ticket Alert*\n\n"
            f"📅 Available dates:\n{dates_text}\n\n"
            f"🎟️ Type: {ticket_type}\n\n"
            f"🔗 [Purchase Now]({purchase_url})"
        )

        await self._send_message(message, parse_mode="Markdown")
        dates_str = ", ".join(a.date.isoformat() for a in available_dates)
        logger.info("Availability alert sent for %s", dates_str)

    async def send_error_alert(self, error_message: str) -> None:
        """Send an error alert message.

        Args:
            error_message: Description of the error.

        Raises:
            NotificationError: If sending fails.
        """
        message = (
            f"⚠️ *Alhambra Checker Error*\n\n"
            f"```\n{error_message}\n```"
        )

        await self._send_message(message, parse_mode="Markdown")
        logger.info("Error alert sent")

    async def _send_message(
        self,
        text: str,
        parse_mode: str | None = None,
    ) -> dict:
        """Send a message via Telegram API.

        Args:
            text: Message text.
            parse_mode: Parse mode (Markdown, HTML, etc.).

        Returns:
            API response data.

        Raises:
            NotificationError: If sending fails.
        """
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": False,
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._api_base}/sendMessage",
                json=payload,
            )

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("description", "Unknown error")
                except (ValueError, KeyError):
                    error_msg = f"HTTP {response.status_code}"
                raise NotificationError(f"Telegram API error: {error_msg}")

            data = response.json()
            if not data.get("ok"):
                raise NotificationError(
                    f"Telegram API error: {data.get('description', 'Unknown error')}"
                )

            return data

    async def test_connection(self) -> bool:
        """Test the Telegram bot connection and send a test message.

        Returns:
            True if connection is successful and test message was sent.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self._api_base}/getMe")
            if not (response.status_code == 200 and response.json().get("ok", False)):
                return False

            bot_info = response.json().get("result", {})
            bot_name = bot_info.get("username", "Unknown")
            logger.info(f"Bot connected: @{bot_name}")

            test_message = "🔔 AlhamBreaker 텔레그램 연결 테스트 성공!\n\n봇이 정상적으로 작동합니다."
            try:
                await self._send_message(test_message)
                logger.info("Test message sent successfully!")
                return True
            except NotificationError as e:
                logger.error(f"Failed to send test message: {e}")
                return False
