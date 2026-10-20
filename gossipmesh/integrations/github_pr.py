import logging
import asyncio
from typing import Any, Dict, List
import httpx

from gossipmesh.core.exceptions import GitHubIntegrationError, RateLimitError

logger = logging.getLogger(__name__)


class GitHubPRService:
    def __init__(self, token: str, max_retries: int = 3, timeout: float = 10.0):
        self.token = token
        self.max_retries = max_retries
        self.timeout = timeout
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make an HTTP request with retry, timeout, and rate limit handling."""
        headers = dict(self.headers)
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        client_kwargs = {"timeout": httpx.Timeout(self.timeout)}

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=client_kwargs["timeout"]) as client:
                    response = await client.request(method, url, headers=headers, **kwargs)

                    if response.status_code in (403, 429):
                        remaining = response.headers.get("x-ratelimit-remaining")
                        if remaining == "0" or response.status_code == 429:
                            raise RateLimitError(
                                message="GitHub API rate limit exceeded",
                                details={"reset": response.headers.get("x-ratelimit-reset")},
                            )

                    if response.status_code >= 500:
                        if attempt == self.max_retries - 1:
                            response.raise_for_status()
                        await asyncio.sleep(2**attempt)
                        continue

                    response.raise_for_status()
                    return response
            except (httpx.TimeoutException, httpx.RequestError) as e:
                if attempt == self.max_retries - 1:
                    raise GitHubIntegrationError(f"Request failed: {str(e)}")
                await asyncio.sleep(2**attempt)
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise GitHubIntegrationError(f"HTTP error: {e.response.status_code} - {e.response.text}")

        raise GitHubIntegrationError("Max retries exceeded")

    async def _get_paginated(self, url: str, **kwargs) -> List[Dict[str, Any]]:
        """Fetch all pages of a paginated GitHub API endpoint."""
        results = []
        next_url: str | None = url

        while next_url:
            response = await self._request("GET", next_url, **kwargs)
            data = response.json()
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)

            # Extract next url from Link header
            link_header = response.headers.get("link")
            next_url = None
            if link_header:
                links = link_header.split(",")
                for link in links:
                    if 'rel="next"' in link:
                        next_url = link[link.find("<") + 1 : link.find(">")]
                        break

        return results

    async def get_pr_metadata(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """Get basic pull request metadata."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        response = await self._request("GET", url)
        return response.json()

    async def get_pr_diff(self, owner: str, repo: str, pull_number: int) -> str:
        """Get pull request unified diff."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
        response = await self._request("GET", url, headers=headers)
        return response.text

    async def get_pr_files(self, owner: str, repo: str, pull_number: int) -> List[Dict[str, Any]]:
        """Get list of changed files in the pull request."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/files"
        return await self._get_paginated(url)

    async def get_pr_commits(self, owner: str, repo: str, pull_number: int) -> List[Dict[str, Any]]:
        """Get list of commits in the pull request."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/commits"
        return await self._get_paginated(url)

    async def get_pr_reviews(self, owner: str, repo: str, pull_number: int) -> List[Dict[str, Any]]:
        """Fetch all reviews for a pull request."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
        return await self._get_paginated(url)

    async def get_pr_details(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """
        Get comprehensive details about a pull request including metadata,
        diff, files, and commits.
        """
        metadata = await self.get_pr_metadata(owner, repo, pull_number)
        diff = await self.get_pr_diff(owner, repo, pull_number)
        files = await self.get_pr_files(owner, repo, pull_number)
        commits = await self.get_pr_commits(owner, repo, pull_number)

        changed_files = [f["filename"] for f in files if "filename" in f]
        file_status = {f["filename"]: f["status"] for f in files if "filename" in f and "status" in f}
        renamed_files = {
            f.get("previous_filename", ""): f["filename"]
            for f in files
            if f.get("status") == "renamed" and "filename" in f
        }

        return {
            "metadata": metadata,
            "base_sha": metadata.get("base", {}).get("sha"),
            "head_sha": metadata.get("head", {}).get("sha"),
            "unified_diff": diff,
            "changed_files": changed_files,
            "file_status": file_status,
            "renamed_files": renamed_files,
            "commits": commits,
            "files_metadata": files,
        }

    async def post_pr_review_comment(
        self, owner: str, repo: str, pull_number: int, comment_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Posts an individual PR review comment.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/comments"
        response = await self._request("POST", url, json=comment_payload)
        return response.json()

    async def post_pr_review(
        self, owner: str, repo: str, pull_number: int, review_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Posts a PR review with inline comments.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
        response = await self._request("POST", url, json=review_payload)
        return response.json()
