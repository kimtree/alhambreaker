"""Playwright browser automation for Alhambra ticket site."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from types import TracebackType

from playwright.async_api import (
    Browser,
    Page,
    Playwright,
    async_playwright,
)
from playwright.async_api import (
    TimeoutError as PlaywrightTimeout,
)

__all__ = ["AlhambraBrowser", "DateAvailability", "TicketStatus"]

logger = logging.getLogger(__name__)

# Month name to number mapping
MONTH_NAMES: dict[str, int] = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}


class TicketStatus(Enum):
    """Ticket availability status."""

    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"
    LAST_TICKETS = "last_tickets"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class DateAvailability:
    """Availability information for a specific date."""

    date: date
    status: TicketStatus
    has_link: bool


class AlhambraBrowser:
    """Browser automation for Alhambra ticket checking."""

    PURCHASE_URL = (
        "https://compratickets.alhambra-patronato.es/reservarEntradas.aspx"
        "?opc=142&gid=432&lg=en-GB&ca=0&m=GENERAL"
    )

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """Initialize browser configuration.

        Args:
            headless: Run browser in headless mode.
            timeout: Default timeout in milliseconds.
        """
        self.headless = headless
        self.timeout = timeout
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def __aenter__(self) -> AlhambraBrowser:
        """Start browser session."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
        )
        self._page = await self._browser.new_page()
        self._page.set_default_timeout(self.timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close browser session."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def navigate_to_purchase_page(self) -> None:
        """Navigate to the ticket purchase page."""
        logger.info("Navigating to purchase page")
        await self._page.goto(self.PURCHASE_URL, wait_until="networkidle")

        # Wait for possible bot check (Voight-Kampff)
        try:
            await self._page.wait_for_selector(
                "text=Go to step 1", timeout=10000
            )
        except PlaywrightTimeout:
            # May need to wait for bot check to complete
            logger.debug("Waiting for bot check...")
            await self._page.wait_for_load_state("networkidle")

    async def accept_cookies(self) -> None:
        """Accept cookie consent if present."""
        try:
            accept_button = self._page.locator(
                "text=Accept everything and continue"
            )
            if await accept_button.is_visible(timeout=3000):
                await accept_button.click()
                logger.info("Cookies accepted")
        except PlaywrightTimeout:
            logger.debug("No cookie consent dialog found")

    async def inject_captcha_token(self, token: str) -> None:
        """Inject the solved reCAPTCHA token into the page.

        Args:
            token: The solved reCAPTCHA token.
        """
        logger.info("Injecting captcha token")

        # Set the token in the hidden textarea and trigger validation
        await self._page.evaluate(
            """(token) => {
                // Find all recaptcha response textareas
                const textareas = document.querySelectorAll(
                    'textarea[name="g-recaptcha-response"], #g-recaptcha-response'
                );
                textareas.forEach(ta => {
                    ta.value = token;
                    ta.innerHTML = token;
                });

                // Also set in iframe if exists
                const iframes = document.querySelectorAll('iframe[src*="recaptcha"]');
                iframes.forEach(iframe => {
                    try {
                        const doc = iframe.contentDocument || iframe.contentWindow.document;
                        const ta = doc.querySelector('textarea');
                        if (ta) ta.value = token;
                    } catch (e) {}
                });

                // Try to find and call the callback function
                // Method 1: grecaptcha callback
                if (typeof grecaptcha !== 'undefined' && grecaptcha.getResponse) {
                    // Override getResponse to return our token
                    grecaptcha.getResponse = () => token;
                }

                // Method 2: ___grecaptcha_cfg clients
                if (typeof ___grecaptcha_cfg !== 'undefined' && ___grecaptcha_cfg.clients) {
                    for (const key in ___grecaptcha_cfg.clients) {
                        const client = ___grecaptcha_cfg.clients[key];
                        if (client) {
                            // Set response directly
                            if (client.G && client.G.V) {
                                client.G.V.response = token;
                            }
                            // Call callback
                            const callbacks = ['callback', 'Ca', 'Ca1'];
                            for (const cb of callbacks) {
                                if (typeof client[cb] === 'function') {
                                    try { client[cb](token); } catch (e) {}
                                }
                            }
                        }
                    }
                }

                // Method 3: Find callback in window
                const callbackNames = [
                    'onRecaptchaSuccess', 'recaptchaCallback', 'captchaCallback',
                    'onCaptchaSuccess', 'validateCaptcha'
                ];
                for (const name of callbackNames) {
                    if (typeof window[name] === 'function') {
                        try { window[name](token); } catch (e) {}
                    }
                }

                // Method 4: Simulate checkbox checked state
                const checkboxes = document.querySelectorAll('.recaptcha-checkbox-checkmark');
                checkboxes.forEach(cb => {
                    cb.style.display = 'block';
                });

                // Mark recaptcha as solved for ASP.NET
                const hiddenField = document.querySelector(
                    'input[name*="captcha"], input[id*="captcha"]'
                );
                if (hiddenField) {
                    hiddenField.value = token;
                }
            }""",
            token,
        )

    async def click_go_to_step1(self) -> None:
        """Click the 'Go to step 1' button to proceed to calendar."""
        logger.info("Clicking 'Go to step 1' button")
        button = self._page.locator("input[value='Go to step 1']")
        await button.click()

        # Wait for calendar to load
        await self._page.wait_for_selector("table", timeout=15000)
        logger.info("Calendar loaded")

    async def navigate_to_month(self, target_date: date) -> None:
        """Navigate the calendar to the target month.

        Args:
            target_date: The target date to navigate to.
        """
        max_attempts = 12  # Max 1 year forward

        for attempt in range(max_attempts):
            # Get current displayed month/year
            current_month_year = await self._get_current_month_year()
            if current_month_year is None:
                logger.warning("Could not determine current calendar month, attempt %d", attempt + 1)
                await self._page.wait_for_timeout(1000)
                continue

            current_year, current_month = current_month_year
            logger.info("Current calendar: %d/%d, Target: %d/%d",
                       current_year, current_month, target_date.year, target_date.month)

            if current_year == target_date.year and current_month == target_date.month:
                logger.info("Reached target month: %s/%s", target_date.year, target_date.month)
                return

            # Need to navigate forward or backward
            if (target_date.year, target_date.month) > (current_year, current_month):
                logger.info("Navigating to next month...")
                await self._click_next_month()
            else:
                logger.info("Navigating to previous month...")
                await self._click_prev_month()

            # Wait for page to update
            await self._page.wait_for_timeout(2000)

        raise RuntimeError(f"Could not navigate to {target_date.year}-{target_date.month}")

    async def _get_current_month_year(self) -> tuple[int, int] | None:
        """Get the currently displayed month and year from calendar.

        Returns:
            Tuple of (year, month) or None if not found.
        """
        month_pattern = "|".join(MONTH_NAMES.keys())

        # Try to get the page content and search for month/year pattern
        try:
            page_content = await self._page.content()
            if match := re.search(
                rf"({month_pattern})\s+(\d{{4}})",
                page_content
            ):
                month_name, year = match.groups()
                logger.debug("Found calendar month: %s %s", month_name, year)
                return int(year), MONTH_NAMES[month_name]
        except PlaywrightTimeout as e:
            logger.warning("Timeout getting page content: %s", e)

        # Fallback: try locator approach
        try:
            cells = self._page.locator("table td")
            count = await cells.count()
            for i in range(min(count, 20)):  # Check first 20 cells
                text = await cells.nth(i).text_content()
                if text and (match := re.search(
                    rf"({month_pattern})\s+(\d{{4}})",
                    text
                )):
                    month_name, year = match.groups()
                    return int(year), MONTH_NAMES[month_name]
        except PlaywrightTimeout as e:
            logger.warning("Timeout getting month/year from cells: %s", e)

        return None

    async def _click_next_month(self) -> None:
        """Click the next month navigation button using JavaScript."""
        # Use JavaScript to click - avoids viewport constraints
        clicked = await self._page.evaluate(
            """() => {
                const links = document.querySelectorAll('a[href*="calendarioFecha"]');
                // Find the last link with an image (next month button is on the right)
                for (let i = links.length - 1; i >= 0; i--) {
                    const link = links[i];
                    if (link.querySelector('img')) {
                        link.click();
                        return true;
                    }
                }
                return false;
            }"""
        )

        if clicked:
            logger.debug("Clicked next month navigation link via JavaScript")
        else:
            logger.warning("Could not find next month navigation link")

        await self._page.wait_for_load_state("networkidle")

    async def _click_prev_month(self) -> None:
        """Click the previous month navigation button using JavaScript."""
        # Use JavaScript to click - avoids viewport constraints
        clicked = await self._page.evaluate(
            """() => {
                const links = document.querySelectorAll('a[href*="calendarioFecha"]');
                // Find the first link with an image (prev month button is on the left)
                for (let i = 0; i < links.length; i++) {
                    const link = links[i];
                    if (link.querySelector('img')) {
                        link.click();
                        return true;
                    }
                }
                return false;
            }"""
        )

        if clicked:
            logger.debug("Clicked prev month navigation link via JavaScript")
        else:
            logger.warning("Could not find prev month navigation link")

        await self._page.wait_for_load_state("networkidle")

    async def check_date_availability(self, target_date: date) -> DateAvailability:
        """Check the availability status of a specific date.

        Args:
            target_date: The date to check.

        Returns:
            DateAvailability with the status information.
        """
        day = target_date.day

        # Find the cell for this day
        # Days with availability have a link, days without don't
        day_cell = self._page.locator(f"table td a:text-is('{day}')")

        try:
            if await day_cell.count() > 0:
                # Has a link - available or last tickets
                # Check the cell's class or style for last_tickets indicator
                has_link = True
                cell = self._page.locator(f"table td:has(a:text-is('{day}'))")
                cell_class = await cell.get_attribute("class") or ""

                if "last" in cell_class.lower() or "ultimo" in cell_class.lower():
                    status = TicketStatus.LAST_TICKETS
                else:
                    status = TicketStatus.AVAILABLE

                logger.info("Date %s is %s", target_date, status.value)
            else:
                # No link - not available
                has_link = False
                status = TicketStatus.NOT_AVAILABLE
                logger.info("Date %s is NOT available", target_date)

        except Exception as e:
            logger.warning("Error checking date availability: %s", e)
            has_link = False
            status = TicketStatus.UNKNOWN

        return DateAvailability(
            date=target_date,
            status=status,
            has_link=has_link,
        )

    async def get_page_url(self) -> str:
        """Get the current page URL."""
        return self._page.url
