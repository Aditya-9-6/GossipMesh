from fastapi import Request, status
from fastapi.responses import JSONResponse
from gossipmesh.core.exceptions import GossipMeshException
import logging

logger = logging.getLogger(__name__)

async def gossipmesh_exception_handler(request: Request, exc: GossipMeshException) -> JSONResponse:
    logger.error(f"GossipMeshException: {exc.error_code} - {exc.message} - Details: {exc.details}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
            }
        },
    )

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
            }
        },
    )

def handle_exceptions(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except GossipMeshException as exc:
            logger.error(f"GossipMeshException: {exc.error_code} - {exc.message}")
            raise exc
        except Exception as exc:
            logger.exception(f"Unhandled exception: {str(exc)}")
            raise exc
    return wrapper
