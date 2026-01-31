"""CLI entry point for Alhambra ticket checker."""

import argparse
import asyncio
import logging
import sys

from .checker import AlhambraChecker
from .config import get_settings


def setup_logging(verbose: bool = False) -> None:
    """Configure logging.

    Args:
        verbose: Enable debug logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Check Alhambra ticket availability and send Telegram alerts"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check availability without sending notifications",
    )
    parser.add_argument(
        "--test-telegram",
        action="store_true",
        help="Test Telegram bot connection",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible mode (for debugging)",
    )

    return parser.parse_args()


async def async_main(args: argparse.Namespace) -> int:
    """Async main function.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    settings = get_settings()

    # Override headless setting if requested (use model_copy to avoid mutating cached settings)
    if args.no_headless:
        settings = settings.model_copy(update={"headless": False})

    checker = AlhambraChecker(settings)

    # Test Telegram connection
    if args.test_telegram:
        logging.info("Testing Telegram connection...")
        if await checker.test_telegram():
            logging.info("Telegram connection successful!")
            return 0
        else:
            logging.error("Telegram connection failed!")
            return 1

    # Run availability check
    logging.info("Target date: %s", settings.target_date)
    logging.info("Ticket type: %s", settings.ticket_type)

    result = await checker.check_availability(dry_run=args.dry_run)

    # Report result
    if result.error:
        logging.error("Check failed: %s", result.error)
        return 1

    logging.info("Status: %s", result.status.value)
    logging.info("Available: %s", result.is_available)

    if result.notification_sent:
        logging.info("Notification sent!")
    elif args.dry_run and result.is_available:
        logging.info("Notification skipped (dry run)")

    return 0


def main() -> None:
    """Main entry point."""
    args = parse_args()
    setup_logging(args.verbose)

    try:
        exit_code = asyncio.run(async_main(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logging.exception("Fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
