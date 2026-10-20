from typing import Any, Dict, Optional


class GossipMeshException(Exception):
    """Base exception for GossipMesh"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class AuthenticationError(GossipMeshException):
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, error_code="AUTHENTICATION_ERROR", details=details)


class AuthorizationError(GossipMeshException):
    def __init__(self, message: str = "Permission denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=403, error_code="AUTHORIZATION_ERROR", details=details)


class ValidationError(GossipMeshException):
    def __init__(self, message: str = "Validation error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=422, error_code="VALIDATION_ERROR", details=details)


class ProviderError(GossipMeshException):
    def __init__(self, message: str = "Provider error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=502, error_code="PROVIDER_ERROR", details=details)


class GitHubIntegrationError(GossipMeshException):
    def __init__(self, message: str = "GitHub integration error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=502, error_code="GITHUB_INTEGRATION_ERROR", details=details)


class DatabaseError(GossipMeshException):
    def __init__(self, message: str = "Database error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, error_code="DATABASE_ERROR", details=details)


class JobFailureError(GossipMeshException):
    def __init__(self, message: str = "Job execution failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, error_code="JOB_FAILURE", details=details)


class SandboxError(GossipMeshException):
    def __init__(self, message: str = "Sandbox error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, error_code="SANDBOX_ERROR", details=details)


class RateLimitError(GossipMeshException):
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_ERROR", details=details)
