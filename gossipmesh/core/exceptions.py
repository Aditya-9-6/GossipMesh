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


class SandboxSecurityError(SandboxError):
    def __init__(self, message: str = "Sandbox security policy violation", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details=details)
        self.error_code = "SANDBOX_SECURITY_VIOLATION"
        self.status_code = 403


class RateLimitError(GossipMeshException):
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_ERROR", details=details)


class ConflictError(GossipMeshException):
    def __init__(
        self, message: str = "Resource conflict or concurrency error", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status_code=409, error_code="CONFLICT_ERROR", details=details)


class ConcurrencyLimitError(GossipMeshException):
    def __init__(
        self, message: str = "Per-tenant concurrency limit exceeded", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status_code=429, error_code="CONCURRENCY_LIMIT_EXCEEDED", details=details)


class NetworkEgressForbiddenError(SandboxSecurityError):
    def __init__(
        self, message: str = "Network egress forbidden by sandbox policy", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details=details)
        self.error_code = "NETWORK_EGRESS_FORBIDDEN"


class LockfileRequiredError(SandboxSecurityError):
    def __init__(
        self,
        message: str = "Dependency installation requires a verified lockfile",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details)
        self.error_code = "LOCKFILE_REQUIRED"


class PlanLimitExceededError(GossipMeshException):
    def __init__(self, message: str = "Plan usage limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=402, error_code="PLAN_LIMIT_EXCEEDED", details=details)


class FeatureNotAvailableInPlanError(AuthorizationError):
    def __init__(
        self,
        message: str = "Feature not available in current subscription plan",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details)
        self.error_code = "FEATURE_NOT_IN_PLAN"
