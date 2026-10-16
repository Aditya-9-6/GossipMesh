import logging
import asyncio
from typing import Any, Dict, List, Optional
import httpx
from datetime import datetime
from sqlalchemy.orm import Session

from gossipmesh.core.exceptions import (
    GitHubIntegrationError,
    GitHubAuthenticationError,
    GitHubAuthorizationError,
    GitHubResourceNotFoundError,
    RateLimitError,
)
from gossipmesh.models.audit import AuditEvent

logger = logging.getLogger(__name__)

class GitHubAPIClient:
    def __init__(self, token: str, max_retries: int = 3, timeout: float = 10.0, db: Optional[Session] = None, actor_id: Optional[int] = None, organization_id: Optional[int] = None):
        self.token = token
        self.max_retries = max_retries
        self.timeout = timeout
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.db = db
        self.actor_id = actor_id
        self.organization_id = organization_id

    def _log_audit_event(self, action: str, details: Dict[str, Any]):
        logger.error(f"{action}", extra={"details": details, "actor_id": self.actor_id, "organization_id": self.organization_id})
        if self.db:
            event = AuditEvent(
                action=action,
                actor_id=self.actor_id,
                organization_id=self.organization_id,
                details=details
            )
            self.db.add(event)
            self.db.commit()

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make an HTTP request with retry, timeout, and typed error handling."""
        headers = dict(self.headers)
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        client_kwargs = {
            "timeout": httpx.Timeout(self.timeout)
        }

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=client_kwargs['timeout']) as client:
                    response = await client.request(method, url, headers=headers, **kwargs)

                    if response.status_code in (403, 429):
                        remaining = response.headers.get("x-ratelimit-remaining")
                        if remaining == "0" or response.status_code == 429:
                            reset_time = response.headers.get("x-ratelimit-reset")
                            details = {"reset": reset_time}
                            self._log_audit_event("github_rate_limit_exceeded", details)
                            raise RateLimitError(
                                message="GitHub API rate limit exceeded",
                                details=details
                            )

                        if response.status_code == 403:
                            self._log_audit_event("github_authorization_error", {"url": url})
                            raise GitHubAuthorizationError(
                                message="GitHub permission denied or access forbidden",
                                details={"url": url, "text": response.text}
                            )

                    if response.status_code == 401:
                        self._log_audit_event("github_authentication_error", {"url": url})
                        raise GitHubAuthenticationError(
                            message="GitHub authentication failed (e.g., token revoked, installation suspended)",
                            details={"url": url, "text": response.text}
                        )

                    if response.status_code == 404:
                        self._log_audit_event("github_resource_not_found", {"url": url})
                        raise GitHubResourceNotFoundError(
                            message="GitHub resource not found (e.g., deleted, renamed, or archived repository, invalid branch)",
                            details={"url": url, "text": response.text}
                        )

                    if response.status_code == 409:
                        self._log_audit_event("github_conflict_error", {"url": url})
                        raise GitHubIntegrationError(
                            message="GitHub conflict error",
                            details={"url": url, "text": response.text},
                            is_transient=False
                        )

                    if response.status_code >= 500:
                        if attempt == self.max_retries - 1:
                            self._log_audit_event("github_server_error", {"url": url, "status_code": response.status_code})
                            raise GitHubIntegrationError(
                                message=f"GitHub API server error: {response.status_code}",
                                details={"url": url, "text": response.text},
                                is_transient=True
                            )
                        # Transient 5xx error, retry
                        retry_after = response.headers.get("Retry-After")
                        sleep_time = int(retry_after) if retry_after else 2 ** attempt
                        await asyncio.sleep(sleep_time)
                        continue

                    response.raise_for_status()
                    return response
            except (httpx.TimeoutException, httpx.RequestError) as e:
                # Network failures or timeouts
                if attempt == self.max_retries - 1:
                    self._log_audit_event("github_network_error", {"url": url, "error": str(e)})
                    raise GitHubIntegrationError(
                        message=f"Request failed: {str(e)}",
                        details={"url": url},
                        is_transient=True
                    )
                await asyncio.sleep(2 ** attempt)
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    retry_after = e.response.headers.get("Retry-After")
                    sleep_time = int(retry_after) if retry_after else 2 ** attempt
                    await asyncio.sleep(sleep_time)
                    continue

                # Should be caught by the explicit checks above, but just in case
                self._log_audit_event("github_http_error", {"url": url, "status_code": e.response.status_code})
                raise GitHubIntegrationError(
                    message=f"HTTP error: {e.response.status_code} - {e.response.text}",
                    details={"url": url},
                    is_transient=False
                )

        raise GitHubIntegrationError("Max retries exceeded", is_transient=True)
