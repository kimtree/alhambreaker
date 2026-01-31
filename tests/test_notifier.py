"""Tests for Telegram notifier module."""

from datetime import date

import pytest

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

        notifier = TelegramNotifier(bot_token="test_token", chat_id="123456")
        await notifier.send_availability_alert(
            target_date=date(2026, 2, 17),
            status="Available",
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

        notifier = TelegramNotifier(bot_token="test_token", chat_id="invalid")

        with pytest.raises(NotificationError) as exc_info:
            await notifier.send_availability_alert(
                target_date=date(2026, 2, 17),
                status="Available",
            )

        assert "chat not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_test_connection_success(self, mocker):
        """Test successful connection test."""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"username": "test_bot"}}

        mock_client = mocker.MagicMock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_client.get = mocker.AsyncMock(return_value=mock_response)

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        notifier = TelegramNotifier(bot_token="test_token", chat_id="123456")
        result = await notifier.test_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, mocker):
        """Test failed connection test."""
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
