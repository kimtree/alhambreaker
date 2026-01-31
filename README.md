# Alhambreaker 🏰

Alhambra ticket availability checker with Telegram notifications.

Monitors the official Alhambra ticket website and sends Telegram alerts when tickets become available for your target date.

## Features

- 🎫 Monitors Alhambra General ticket availability
- 🤖 Automatic reCAPTCHA solving via 2Captcha
- 📱 Telegram notifications when tickets become available
- 🔄 Designed for periodic execution via cron/systemd
- 🧪 Comprehensive test suite with mocking

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- 2Captcha API key ([Get one here](https://2captcha.com))
- Telegram Bot token ([Create via @BotFather](https://t.me/botfather))

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/alhambreaker.git
cd alhambreaker
```

### 2. Install dependencies with uv

```bash
uv sync
```

### 3. Install Playwright browsers

```bash
uv run playwright install chromium
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

## Configuration

Create a `.env` file with the following variables:

```env
# 2Captcha API Key (required)
CAPTCHA_API_KEY=your_2captcha_api_key

# Telegram Bot Configuration (required)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Target Date to Monitor (required, YYYY-MM-DD format)
TARGET_DATE=2026-02-17

# Ticket Type (optional, default: GENERAL)
TICKET_TYPE=GENERAL

# Browser Settings (optional)
HEADLESS=true
BROWSER_TIMEOUT=30000
```

### Getting Your Telegram Chat ID

1. Start a chat with [@userinfobot](https://t.me/userinfobot)
2. The bot will reply with your chat ID

## Usage

### Basic check

```bash
uv run python -m alhambreaker
```

### Dry run (no notifications)

```bash
uv run python -m alhambreaker --dry-run
```

### Verbose output

```bash
uv run python -m alhambreaker -v
```

### Test Telegram connection

```bash
uv run python -m alhambreaker --test-telegram
```

### Debug mode (visible browser)

```bash
uv run python -m alhambreaker --no-headless
```

## Scheduled Execution

### Using cron (every 30 minutes)

```bash
crontab -e

# Add this line
*/30 * * * * cd /home/user/alhambreaker && ./.venv/bin/python -m alhambreaker >> ~/alhambreaker.log 2>&1
```

### Using systemd timer

Create `/etc/systemd/system/alhambreaker.service`:

```ini
[Unit]
Description=Alhambra Ticket Checker

[Service]
Type=oneshot
WorkingDirectory=/path/to/alhambreaker
ExecStart=/path/to/.venv/bin/python -m alhambreaker
User=ubuntu
```

Create `/etc/systemd/system/alhambreaker.timer`:

```ini
[Unit]
Description=Run Alhambra Ticket Checker every 15 minutes

[Timer]
OnCalendar=*:0/15
Persistent=true

[Install]
WantedBy=timers.target
```

Enable the timer:

```bash
sudo systemctl enable alhambreaker.timer
sudo systemctl start alhambreaker.timer
```

## Development

### Install dev dependencies

```bash
uv sync --all-extras
```

### Run tests

```bash
uv run pytest
```

### Run tests with coverage

```bash
uv run pytest --cov=alhambreaker
```

### Lint code

```bash
uv run ruff check .
```

### Format code

```bash
uv run ruff format .
```

### Setup pre-commit hooks

```bash
uv run pre-commit install
```

## Project Structure

```
alhambreaker/
├── pyproject.toml           # Project configuration
├── .env.example             # Environment variables template
├── .pre-commit-config.yaml  # Pre-commit hooks
├── README.md
├── src/
│   └── alhambreaker/
│       ├── __init__.py
│       ├── __main__.py      # CLI entry point
│       ├── config.py        # Settings management
│       ├── checker.py       # Main orchestration logic
│       ├── browser.py       # Playwright browser automation
│       ├── captcha.py       # 2Captcha integration
│       └── notifier.py      # Telegram notifications
└── tests/
    ├── conftest.py          # Pytest fixtures
    ├── test_browser.py
    ├── test_captcha.py
    ├── test_checker.py
    ├── test_config.py
    └── test_notifier.py
```

## How It Works

1. **Navigate** to the Alhambra ticket purchase page
2. **Solve** reCAPTCHA using 2Captcha service
3. **Inject** the solved token and proceed to calendar
4. **Navigate** to the target month
5. **Check** if the target date has available tickets
6. **Notify** via Telegram if tickets are available

## Cost Estimation

- 2Captcha: ~$2.99 per 1000 reCAPTCHA solves
- Running every 15 minutes = 96 checks/day = ~$0.29/day
- Monthly cost: ~$8.70

## Troubleshooting

### "Voight-Kampff Browser Test" blocking

The site has bot detection. If you're getting blocked:
- Try running with `--no-headless` to debug
- The current implementation should handle most cases

### reCAPTCHA image challenges

2Captcha handles both checkbox and image challenges. Image challenges may take longer and cost slightly more.

### Telegram notifications not working

1. Check your bot token with `--test-telegram`
2. Ensure you've started a chat with your bot
3. Verify your chat ID is correct

## License

MIT License - see LICENSE file for details.

## Disclaimer

This tool is for personal use only. Please respect the Alhambra's terms of service and don't abuse the checking frequency. The recommended interval is 15 minutes or longer.
