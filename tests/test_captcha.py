"""Tests for captcha solver module."""

import pytest

from alhambreaker.captcha import CaptchaError, CaptchaSolver


class TestCaptchaSolver:
    """Tests for CaptchaSolver class."""

    def test_init(self):
        """Test solver initialization."""
        solver = CaptchaSolver(
            api_key="test_key",
            timeout=60,
            poll_interval=3,
            max_retries=5,
        )

        assert solver.api_key == "test_key"
        assert solver.timeout == 60
        assert solver.poll_interval == 3
        assert solver.max_retries == 5

    def test_init_defaults(self):
        """Test solver initialization with defaults."""
        solver = CaptchaSolver(api_key="test_key")

        assert solver.timeout == 180
        assert solver.poll_interval == 5
        assert solver.max_retries == 3

    @pytest.mark.asyncio
    async def test_solve_recaptcha_success(self, httpx_mock):
        """Test successful captcha solving."""
        # Mock submit task response
        httpx_mock.add_response(
            url="https://2captcha.com/in.php",
            json={"status": 1, "request": "task123"},
        )

        # Mock poll result responses
        httpx_mock.add_response(
            url="https://2captcha.com/res.php",
            json={"status": 0, "request": "CAPCHA_NOT_READY"},
        )
        httpx_mock.add_response(
            url="https://2captcha.com/res.php",
            json={"status": 1, "request": "solved_token_123"},
        )

        solver = CaptchaSolver(api_key="test_key", poll_interval=0)
        token = await solver.solve_recaptcha(
            site_key="test_site_key",
            page_url="https://example.com",
        )

        assert token == "solved_token_123"

    @pytest.mark.asyncio
    async def test_solve_recaptcha_submit_error(self, httpx_mock):
        """Test captcha solving with submit error."""
        httpx_mock.add_response(
            url="https://2captcha.com/in.php",
            json={"status": 0, "request": "ERROR_WRONG_USER_KEY"},
        )

        solver = CaptchaSolver(api_key="wrong_key")

        with pytest.raises(CaptchaError) as exc_info:
            await solver.solve_recaptcha(
                site_key="test_site_key",
                page_url="https://example.com",
            )

        assert "ERROR_WRONG_USER_KEY" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_solve_recaptcha_solve_error(self, httpx_mock):
        """Test captcha solving with solve error."""
        httpx_mock.add_response(
            url="https://2captcha.com/in.php",
            json={"status": 1, "request": "task123"},
        )
        httpx_mock.add_response(
            url="https://2captcha.com/res.php",
            json={"status": 0, "request": "ERROR_CAPTCHA_UNSOLVABLE"},
        )

        solver = CaptchaSolver(api_key="test_key", poll_interval=0)

        with pytest.raises(CaptchaError) as exc_info:
            await solver.solve_recaptcha(
                site_key="test_site_key",
                page_url="https://example.com",
            )

        assert "ERROR_CAPTCHA_UNSOLVABLE" in str(exc_info.value)


@pytest.fixture
def httpx_mock(mocker):
    """Mock httpx client responses."""
    import httpx

    mock_responses = []

    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json = json_data
            self.status_code = status_code

        def json(self):
            return self._json

        def raise_for_status(self):
            pass

    class MockAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            del args, kwargs  # unused
            if mock_responses:
                return mock_responses.pop(0)
            return MockResponse({})

        async def post(self, *args, **kwargs):
            del args, kwargs  # unused
            if mock_responses:
                return mock_responses.pop(0)
            return MockResponse({})

    mock_client = MockAsyncClient()

    def add_response(**kwargs):
        """Add a response to the mock queue. Accepts url, json, status_code."""
        json_data = kwargs.get("json")
        status_code = kwargs.get("status_code", 200)
        mock_responses.append(MockResponse(json_data, status_code))

    mocker.patch.object(httpx, "AsyncClient", return_value=mock_client)

    mock_client.add_response = add_response
    return mock_client
