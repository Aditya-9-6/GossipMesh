import uuid
import contextvars

correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


class CorrelationIdMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Extract X-Correlation-ID from headers
        req_id = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-correlation-id":
                req_id = value.decode("latin1")
                break

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

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = message.get("headers", [])
                    headers.append((b"x-correlation-id", req_id.encode("latin1")))
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_wrapper)
        finally:
            correlation_id.reset(token)


def get_correlation_id() -> str:
    return correlation_id.get()
