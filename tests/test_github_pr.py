import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import Response
from gossipmesh.integrations.github_pr import GitHubPRService
from gossipmesh.core.exceptions import GitHubIntegrationError, RateLimitError
import asyncio


@pytest.fixture
def github_pr_service():
    return GitHubPRService(token="test_token", max_retries=3, timeout=1.0)


@pytest.mark.asyncio
async def test_get_pr_metadata_success(github_pr_service):
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request_obj = MagicMock()
        mock_response = Response(200, json={"id": 1, "number": 42, "state": "open"}, request=mock_request_obj)
        mock_request.return_value = mock_response

        metadata = await github_pr_service.get_pr_metadata("owner", "repo", 42)

        assert metadata["id"] == 1
        assert metadata["number"] == 42
        mock_request.assert_called_once_with(
            "GET",
            "https://api.github.com/repos/owner/repo/pulls/42",
            headers=github_pr_service.headers
        )


@pytest.mark.asyncio
async def test_get_pr_diff_success(github_pr_service):
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request_obj = MagicMock()
        mock_response = Response(200, text="--- a/file\n+++ b/file\n@@ -1 +1 @@", request=mock_request_obj)
        mock_request.return_value = mock_response

        diff = await github_pr_service.get_pr_diff("owner", "repo", 42)

        assert diff == "--- a/file\n+++ b/file\n@@ -1 +1 @@"

        expected_headers = dict(github_pr_service.headers)
        expected_headers["Accept"] = "application/vnd.github.v3.diff"
        mock_request.assert_called_once_with(
            "GET",
            "https://api.github.com/repos/owner/repo/pulls/42",
            headers=expected_headers
        )


@pytest.mark.asyncio
async def test_pagination(github_pr_service):
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
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

        files = await github_pr_service.get_pr_files("owner", "repo", 42)

        assert len(files) == 2
        assert files[0]["filename"] == "file1.txt"
        assert files[1]["filename"] == "file2.txt"
        assert mock_request.call_count == 2


@pytest.mark.asyncio
async def test_retry_policy_server_error(github_pr_service):
    # Mock sleep to avoid actually waiting during test
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:

        mock_request_obj = MagicMock()
        # 2 failures followed by 1 success
        mock_request.side_effect = [
            Response(500, request=mock_request_obj),
            Response(502, request=mock_request_obj),
            Response(200, json={"status": "success"}, request=mock_request_obj)
        ]

        metadata = await github_pr_service.get_pr_metadata("owner", "repo", 42)

        assert metadata == {"status": "success"}
        assert mock_request.call_count == 3
        assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_retry_policy_timeout(github_pr_service):
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:

        mock_request_obj = MagicMock()
        mock_request.side_effect = [
            httpx.TimeoutException("Timeout"),
            Response(200, json={"status": "success"}, request=mock_request_obj)
        ]

        metadata = await github_pr_service.get_pr_metadata("owner", "repo", 42)

        assert metadata == {"status": "success"}
        assert mock_request.call_count == 2


@pytest.mark.asyncio
async def test_rate_limit_exceeded(github_pr_service):
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request_obj = MagicMock()
        mock_request.return_value = Response(
            403,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1234567890"},
            request=mock_request_obj
        )

        with pytest.raises(RateLimitError) as exc_info:
            await github_pr_service.get_pr_metadata("owner", "repo", 42)

        assert exc_info.value.status_code == 429
        assert exc_info.value.error_code == "RATE_LIMIT_ERROR"


@pytest.mark.asyncio
async def test_get_pr_details_comprehensive(github_pr_service):
    with patch.object(github_pr_service, "get_pr_metadata", new_callable=AsyncMock) as mock_metadata, \
         patch.object(github_pr_service, "get_pr_diff", new_callable=AsyncMock) as mock_diff, \
         patch.object(github_pr_service, "get_pr_files", new_callable=AsyncMock) as mock_files, \
         patch.object(github_pr_service, "get_pr_commits", new_callable=AsyncMock) as mock_commits:

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

        details = await github_pr_service.get_pr_details("owner", "repo", 42)

        assert details["base_sha"] == "base123"
        assert details["head_sha"] == "head456"
        assert details["unified_diff"] == "diff content"
        assert details["changed_files"] == ["modified.txt", "new_name.txt"]
        assert details["file_status"] == {"modified.txt": "modified", "new_name.txt": "renamed"}
        assert details["renamed_files"] == {"old_name.txt": "new_name.txt"}
        assert len(details["commits"]) == 2
