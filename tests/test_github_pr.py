import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import Response
import httpx
from gossipmesh.integrations.github_pr import GitHubPRService
from gossipmesh.core.exceptions import RateLimitError

class TestGitHubPRService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.github_pr_service = GitHubPRService(token="test_token", max_retries=3, timeout=1.0)

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_get_pr_metadata_success(self, mock_request):
        mock_request_obj = MagicMock()
        mock_response = Response(200, json={"id": 1, "number": 42, "state": "open"}, request=mock_request_obj)
        mock_request.return_value = mock_response

        metadata = await self.github_pr_service.get_pr_metadata("owner", "repo", 42)

        self.assertEqual(metadata["id"], 1)
        self.assertEqual(metadata["number"], 42)
        mock_request.assert_called_once_with(
            "GET",
            "https://api.github.com/repos/owner/repo/pulls/42",
            headers=self.github_pr_service.headers
        )

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_get_pr_diff_success(self, mock_request):
        mock_request_obj = MagicMock()
        mock_response = Response(200, text="--- a/file\n+++ b/file\n@@ -1 +1 @@", request=mock_request_obj)
        mock_request.return_value = mock_response

        diff = await self.github_pr_service.get_pr_diff("owner", "repo", 42)

        self.assertEqual(diff, "--- a/file\n+++ b/file\n@@ -1 +1 @@")

        expected_headers = dict(self.github_pr_service.headers)
        expected_headers["Accept"] = "application/vnd.github.v3.diff"
        mock_request.assert_called_once_with(
            "GET",
            "https://api.github.com/repos/owner/repo/pulls/42",
            headers=expected_headers
        )

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_pagination(self, mock_request):
        mock_request_obj = MagicMock()
        response_page_1 = Response(
            200,
            json=[{"filename": "file1.txt"}],
            headers={"link": '<https://api.github.com/resource?page=2>; rel="next"'},
            request=mock_request_obj
        )
        response_page_2 = Response(
            200,
            json=[{"filename": "file2.txt"}],
            request=mock_request_obj
        )
        mock_request.side_effect = [response_page_1, response_page_2]

        files = await self.github_pr_service.get_pr_files("owner", "repo", 42)

        self.assertEqual(len(files), 2)
        self.assertEqual(files[0]["filename"], "file1.txt")
        self.assertEqual(files[1]["filename"], "file2.txt")
        self.assertEqual(mock_request.call_count, 2)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_retry_policy_server_error(self, mock_request, mock_sleep):
        mock_request_obj = MagicMock()
        # 2 failures followed by 1 success
        mock_request.side_effect = [
            Response(500, request=mock_request_obj),
            Response(502, request=mock_request_obj),
            Response(200, json={"status": "success"}, request=mock_request_obj)
        ]

        metadata = await self.github_pr_service.get_pr_metadata("owner", "repo", 42)

        self.assertEqual(metadata, {"status": "success"})
        self.assertEqual(mock_request.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_retry_policy_timeout(self, mock_request, mock_sleep):
        mock_request_obj = MagicMock()
        mock_request.side_effect = [
            httpx.TimeoutException("Timeout"),
            Response(200, json={"status": "success"}, request=mock_request_obj)
        ]

        metadata = await self.github_pr_service.get_pr_metadata("owner", "repo", 42)

        self.assertEqual(metadata, {"status": "success"})
        self.assertEqual(mock_request.call_count, 2)

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    async def test_rate_limit_exceeded(self, mock_request):
        mock_request_obj = MagicMock()
        mock_request.return_value = Response(
            403,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1234567890"},
            request=mock_request_obj
        )

        with self.assertRaises(RateLimitError) as context:
            await self.github_pr_service.get_pr_metadata("owner", "repo", 42)

        self.assertEqual(context.exception.status_code, 429)
        self.assertEqual(context.exception.error_code, "RATE_LIMIT_ERROR")

    async def test_get_pr_details_comprehensive(self):
        with patch.object(self.github_pr_service, "get_pr_metadata", new_callable=AsyncMock) as mock_metadata, \
             patch.object(self.github_pr_service, "get_pr_diff", new_callable=AsyncMock) as mock_diff, \
             patch.object(self.github_pr_service, "get_pr_files", new_callable=AsyncMock) as mock_files, \
             patch.object(self.github_pr_service, "get_pr_commits", new_callable=AsyncMock) as mock_commits:

            mock_metadata.return_value = {
                "id": 1,
                "base": {"sha": "base123"},
                "head": {"sha": "head456"}
            }
            mock_diff.return_value = "diff content"
            mock_files.return_value = [
                {"filename": "modified.txt", "status": "modified"},
                {"filename": "new_name.txt", "previous_filename": "old_name.txt", "status": "renamed"}
            ]
            mock_commits.return_value = [{"sha": "commit1"}, {"sha": "commit2"}]

            details = await self.github_pr_service.get_pr_details("owner", "repo", 42)

            self.assertEqual(details["base_sha"], "base123")
            self.assertEqual(details["head_sha"], "head456")
            self.assertEqual(details["unified_diff"], "diff content")
            self.assertEqual(details["changed_files"], ["modified.txt", "new_name.txt"])
            self.assertEqual(details["file_status"], {"modified.txt": "modified", "new_name.txt": "renamed"})
            self.assertEqual(details["renamed_files"], {"old_name.txt": "new_name.txt"})
            self.assertEqual(len(details["commits"]), 2)

if __name__ == '__main__':
    unittest.main()
