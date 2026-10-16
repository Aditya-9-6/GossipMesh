import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import Response
import httpx
from gossipmesh.integrations.github_client import GitHubAPIClient
from gossipmesh.core.exceptions import (
    GitHubIntegrationError,
    GitHubAuthenticationError,
    GitHubAuthorizationError,
    GitHubResourceNotFoundError,
    RateLimitError,
)

class TestGitHubAPIClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.client = GitHubAPIClient(
            token="test_token",
            max_retries=3,
            timeout=1.0,
            db=self.mock_db,
            actor_id=1,
            organization_id=1
        )

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_successful_request(self, mock_request):
        mock_request_obj = MagicMock()
        mock_response = Response(200, json={"status": "ok"}, request=mock_request_obj)
        mock_request.return_value = mock_response

        response = await self.client._request("GET", "https://api.github.com/test")

        self.assertEqual(response.json(), {"status": "ok"})
        mock_request.assert_called_once()
        self.mock_db.add.assert_not_called()

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_authentication_error(self, mock_request):
        mock_request_obj = MagicMock()
        mock_response = Response(401, text="Bad credentials", request=mock_request_obj)
        mock_request.return_value = mock_response

        with self.assertRaises(GitHubAuthenticationError) as context:
            await self.client._request("GET", "https://api.github.com/test")

        self.assertEqual(context.exception.status_code, 401)
        self.assertFalse(context.exception.is_transient)
        self.assertTrue(self.mock_db.add.called)

        audit_event = self.mock_db.add.call_args[0][0]
        self.assertEqual(audit_event.action, "github_authentication_error")

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_authorization_error(self, mock_request):
        mock_request_obj = MagicMock()
        mock_response = Response(403, text="Forbidden", headers={"x-ratelimit-remaining": "10"}, request=mock_request_obj)
        mock_request.return_value = mock_response

        with self.assertRaises(GitHubAuthorizationError) as context:
            await self.client._request("GET", "https://api.github.com/test")

        self.assertEqual(context.exception.status_code, 403)
        self.assertFalse(context.exception.is_transient)
        self.assertTrue(self.mock_db.add.called)

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_resource_not_found_error(self, mock_request):
        mock_request_obj = MagicMock()
        mock_response = Response(404, text="Not Found", request=mock_request_obj)
        mock_request.return_value = mock_response

        with self.assertRaises(GitHubResourceNotFoundError) as context:
            await self.client._request("GET", "https://api.github.com/test")

        self.assertEqual(context.exception.status_code, 404)
        self.assertFalse(context.exception.is_transient)
        self.assertTrue(self.mock_db.add.called)

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_rate_limit_error(self, mock_request):
        mock_request_obj = MagicMock()
        mock_response = Response(429, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1234567890"}, request=mock_request_obj)
        mock_request.return_value = mock_response

        with self.assertRaises(RateLimitError) as context:
            await self.client._request("GET", "https://api.github.com/test")

        self.assertEqual(context.exception.status_code, 429)
        self.assertTrue(self.mock_db.add.called)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_transient_5xx_error_retries(self, mock_request, mock_sleep):
        mock_request_obj = MagicMock()

        # 2 failures followed by 1 success
        mock_request.side_effect = [
            Response(502, text="Bad Gateway", request=mock_request_obj),
            Response(500, text="Internal Server Error", headers={"Retry-After": "5"}, request=mock_request_obj),
            Response(200, json={"status": "ok"}, request=mock_request_obj)
        ]

        response = await self.client._request("GET", "https://api.github.com/test")

        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(mock_request.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

        # First sleep is default backoff (2**0 = 1)
        mock_sleep.assert_any_call(1)
        # Second sleep uses Retry-After header
        mock_sleep.assert_any_call(5)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_transient_5xx_error_max_retries(self, mock_request, mock_sleep):
        mock_request_obj = MagicMock()
        mock_request.return_value = Response(503, text="Service Unavailable", request=mock_request_obj)

        with self.assertRaises(GitHubIntegrationError) as context:
            await self.client._request("GET", "https://api.github.com/test")

        self.assertTrue(context.exception.is_transient)
        self.assertEqual(mock_request.call_count, 3)
        self.assertTrue(self.mock_db.add.called)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_network_timeout(self, mock_request, mock_sleep):
        mock_request.side_effect = [
            httpx.TimeoutException("Read timeout"),
            httpx.ConnectError("Connection refused"),
            httpx.TimeoutException("Read timeout")
        ]

        with self.assertRaises(GitHubIntegrationError) as context:
            await self.client._request("GET", "https://api.github.com/test")

        self.assertTrue(context.exception.is_transient)
        self.assertEqual(mock_request.call_count, 3)
        self.assertTrue(self.mock_db.add.called)

if __name__ == '__main__':
    unittest.main()
