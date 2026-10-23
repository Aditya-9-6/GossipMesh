import time
from typing import Optional, Callable
from fastapi import Request, Response, Depends, HTTPException
import jwt

from gossipmesh.core.rate_limit import RateLimiter
from gossipmesh.core.config import settings


def get_org_id_from_request(request: Request) -> Optional[int]:
    """Extract organization ID from the request if possible."""
    org_id = request.path_params.get("organization_id")
    if org_id:
        try:
            return int(org_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid organization_id format")

    org_id = request.query_params.get("organization_id")
    if org_id:
        try:
            return int(org_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid organization_id format")

    return None


def get_identifier(request: Request) -> str:
    """Get the identifier for rate limiting."""
    org_id = get_org_id_from_request(request)
    if org_id:
        return f"org:{org_id}"

    # Check for authorization header to get user
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass

    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


def rate_limit(limit_type: str, limit: int, window: int):
    limiter = RateLimiter(limit, window)

    async def dependency(request: Request, response: Response):
        identifier = get_identifier(request)

        try:
            remaining, reset_time = limiter.enforce(identifier, limit_type)
        except Exception as exc:
            raise exc

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

    return dependency
