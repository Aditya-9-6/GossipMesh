import uuid
import contextvars
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # We don't trust user input for security context, so we strictly validate it
        req_id = request.headers.get("X-Correlation-ID")

        if req_id:
            try:
                # Validate it's a UUID to prevent injection attacks if it's logged
                val = uuid.UUID(req_id, version=4)
                req_id = str(val)
            except ValueError:
                req_id = str(uuid.uuid4())
        else:
            req_id = str(uuid.uuid4())

        token = correlation_id.set(req_id)

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = req_id
            return response
        finally:
            correlation_id.reset(token)

def get_correlation_id() -> str:
    return correlation_id.get()
