"""Tests for Telegram notifier module."""

from datetime import date

import pytest

from alhambreaker.browser import DateAvailability, TicketStatus
from alhambreaker.notifier import NotificationError, TelegramNotifier


class TestTelegramNotifier:
    """Tests for TelegramNotifier class."""

    def test_init(self):
        """Test notifier initialization."""
        notifier = TelegramNotifier(
            bot_token="test_token",
            chat_id="123456",
        )

        assert notifier.bot_token == "test_token"
        assert notifier.chat_id == "123456"
        assert "test_token" in notifier._api_base

    @pytest.mark.asyncio
    async def test_send_availability_alert_success(self, mocker):
        """Test successful availability alert."""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {}}

        mock_client = mocker.MagicMock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_client.post = mocker.AsyncMock(return_value=mock_response)

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        available_dates = [
            DateAvailability(
                date=date(2026, 2, 17),
                status=TicketStatus.AVAILABLE,
                has_link=True,
            )
        ]

        notifier = TelegramNotifier(bot_token="test_token", chat_id="123456")
        await notifier.send_availability_alert(
            available_dates=available_dates,
            ticket_type="GENERAL",
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "sendMessage" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["chat_id"] == "123456"
        assert "2026-02-17" in payload["text"]
        assert "Available" in payload["text"]

    @pytest.mark.asyncio
    async def test_send_availability_alert_multiple_dates(self, mocker):
        """Test availability alert with multiple dates."""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {}}

        mock_client = mocker.MagicMock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_client.post = mocker.AsyncMock(return_value=mock_response)

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        available_dates = [
            DateAvailability(
                date=date(2026, 2, 17),
                status=TicketStatus.AVAILABLE,
                has_link=True,
            ),
            DateAvailability(
                date=date(2026, 2, 20),
                status=TicketStatus.LAST_TICKETS,
                has_link=True,
            ),
        ]

        notifier = TelegramNotifier(bot_token="test_token", chat_id="123456")
        await notifier.send_availability_alert(
            available_dates=available_dates,
            ticket_type="GENERAL",
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert "2026-02-17" in payload["text"]
        assert "2026-02-20" in payload["text"]
        assert "Last Tickets" in payload["text"]

    @pytest.mark.asyncio
    async def test_send_availability_alert_failure(self, mocker):
        """Test availability alert failure handling."""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "ok": False,
            "description": "Bad Request: chat not found",
        }

        mock_client = mocker.MagicMock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_client.post = mocker.AsyncMock(return_value=mock_response)

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        available_dates = [
            DateAvailability(
                date=date(2026, 2, 17),
                status=TicketStatus.AVAILABLE,
                has_link=True,
            )
        ]

        notifier = TelegramNotifier(bot_token="test_token", chat_id="invalid")

        with pytest.raises(NotificationError) as exc_info:
            await notifier.send_availability_alert(available_dates=available_dates)

        assert "chat not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_test_connection_success(self, mocker):
        """Test successful connection test with test message."""
        mock_get_response = mocker.MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "ok": True,
            "result": {"username": "test_bot"},
        }

        mock_post_response = mocker.MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"ok": True, "result": {}}

        mock_client = mocker.MagicMock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_client.get = mocker.AsyncMock(return_value=mock_get_response)
        mock_client.post = mocker.AsyncMock(return_value=mock_post_response)

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        notifier = TelegramNotifier(bot_token="test_token", chat_id="123456")
        result = await notifier.test_connection()

        assert result is True
        mock_client.get.assert_called_once()
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "sendMessage" in call_args[0][0]
        payload = call_args[1]["json"]
        assert "테스트 성공" in payload["text"]

    @pytest.mark.asyncio
    async def test_test_connection_failure_invalid_token(self, mocker):
        """Test failed connection test with invalid token."""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"ok": False}

        mock_client = mocker.MagicMock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_client.get = mocker.AsyncMock(return_value=mock_response)

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        notifier = TelegramNotifier(bot_token="invalid_token", chat_id="123456")
        result = await notifier.test_connection()

        assert result is False
        mock_client.get.assert_called_once()
        mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_test_connection_failure_send_message(self, mocker):
        """Test connection test fails when test message cannot be sent."""
        mock_get_response = mocker.MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "ok": True,
            "result": {"username": "test_bot"},
        }

        mock_post_response = mocker.MagicMock()
        mock_post_response.status_code = 400
        mock_post_response.json.return_value = {
            "ok": False,
            "description": "Bad Request: chat not found",
        }

        mock_client = mocker.MagicMock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_client.get = mocker.AsyncMock(return_value=mock_get_response)
        mock_client.post = mocker.AsyncMock(return_value=mock_post_response)

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        notifier = TelegramNotifier(bot_token="test_token", chat_id="invalid_chat")
        result = await notifier.test_connection()

        assert result is False
        mock_client.get.assert_called_once()
        mock_client.post.assert_called_once()
