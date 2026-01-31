"""2Captcha integration for solving reCAPTCHA v2."""

import asyncio
import logging

import httpx

__all__ = ["CaptchaSolver", "CaptchaError"]

logger = logging.getLogger(__name__)

TWOCAPTCHA_API_URL = "https://2captcha.com"


class CaptchaError(Exception):
    """Base exception for captcha-related errors."""


class CaptchaSolver:
    """Solves reCAPTCHA v2 using 2Captcha service."""

    def __init__(self, api_key: str, timeout: int = 120, poll_interval: int = 5):
        """Initialize the captcha solver.

        Args:
            api_key: 2Captcha API key.
            timeout: Maximum time to wait for solution in seconds.
            poll_interval: Time between polling attempts in seconds.
        """
        self.api_key = api_key
        self.timeout = timeout
        self.poll_interval = poll_interval

    async def solve_recaptcha(self, site_key: str, page_url: str) -> str:
        """Solve a reCAPTCHA v2 challenge.

        Args:
            site_key: The reCAPTCHA site key.
            page_url: The URL of the page with the captcha.

        Returns:
            The solved captcha token.

        Raises:
            CaptchaError: If solving fails.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Submit captcha task
            task_id = await self._submit_task(client, site_key, page_url)
            logger.info("Captcha task submitted: %s", task_id)

            # Poll for result
            token = await self._poll_result(client, task_id)
            logger.info("Captcha solved successfully")

            return token

    async def _submit_task(
        self, client: httpx.AsyncClient, site_key: str, page_url: str
    ) -> str:
        """Submit a captcha solving task to 2Captcha.

        Args:
            client: HTTP client.
            site_key: The reCAPTCHA site key.
            page_url: The URL of the page with the captcha.

        Returns:
            The task ID.

        Raises:
            CaptchaError: If submission fails.
        """
        response = await client.get(
            f"{TWOCAPTCHA_API_URL}/in.php",
            params={
                "key": self.api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "json": 1,
            },
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != 1:
            error_text = data.get("request", "Unknown error")
            raise CaptchaError(f"Failed to submit captcha task: {error_text}")

        return data["request"]

    async def _poll_result(self, client: httpx.AsyncClient, task_id: str) -> str:
        """Poll for captcha solving result.

        Args:
            client: HTTP client.
            task_id: The task ID to poll.

        Returns:
            The solved captcha token.

        Raises:
            CaptchaError: If polling fails or times out.
        """
        elapsed = 0
        # Initial delay before first poll (captcha solving takes time)
        await asyncio.sleep(10)
        elapsed += 10

        while elapsed < self.timeout:
            response = await client.get(
                f"{TWOCAPTCHA_API_URL}/res.php",
                params={
                    "key": self.api_key,
                    "action": "get",
                    "id": task_id,
                    "json": 1,
                },
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == 1:
                return data["request"]

            error_text = data.get("request", "")
            if error_text == "CAPCHA_NOT_READY":
                logger.debug("Captcha not ready, waiting...")
                await asyncio.sleep(self.poll_interval)
                elapsed += self.poll_interval
            else:
                raise CaptchaError(f"Captcha solving failed: {error_text}")

        raise CaptchaError(f"Captcha solving timed out after {self.timeout}s")

    async def report_bad(self, task_id: str) -> None:
        """Report an incorrect captcha solution for refund.

        Args:
            task_id: The task ID to report.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.get(
                f"{TWOCAPTCHA_API_URL}/res.php",
                params={
                    "key": self.api_key,
                    "action": "reportbad",
                    "id": task_id,
                },
            )
            logger.info("Reported bad captcha: %s", task_id)
