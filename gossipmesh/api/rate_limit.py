from typing import Optional
from fastapi import Request, Response
import jwt

from gossipmesh.core.rate_limit import RateLimiter
from gossipmesh.core.config import settings

import json

async def get_org_id_from_request(request: Request) -> Optional[int]:
    """Extract organization ID from the request if possible."""
    org_id = request.path_params.get("organization_id")
    if org_id:
        try:
            return int(org_id)
        except ValueError:
            pass

    org_id = request.query_params.get("organization_id")
    if org_id:
        try:
            return int(org_id)
        except ValueError:
            pass

    # Try parsing body (since some requests pass organization_id in body)
    try:
        # Cache body to prevent consuming stream
        body = await request.body()
        if body:
            data = json.loads(body)
            if isinstance(data, dict) and "organization_id" in data:
                return int(data["organization_id"])
    except Exception:
        pass

    return None

async def get_identifier(request: Request) -> str:
    """Get the identifier for rate limiting."""
    org_id = await get_org_id_from_request(request)
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
        identifier = await get_identifier(request)

        # Enforce rate limit (this will raise RateLimitError if exceeded)
        # Note: If it raises RateLimitError, the exception handler needs to set the headers!
        try:
            remaining, reset_time = limiter.enforce(identifier, limit_type)
        except Exception as exc:
            # We catch it, set headers on response, then re-raise
            # Wait, if we raise, the headers on the `response` object might not be returned
            # if we use a global exception handler. We need to handle this in exception handler
            # or raise HTTPException directly.
            # We will handle it by raising and the exception handler will add headers
            raise exc

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

    return dependency
