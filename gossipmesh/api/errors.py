from fastapi import Request, status
from fastapi.responses import JSONResponse
from gossipmesh.core.exceptions import GossipMeshException
import logging

logger = logging.getLogger(__name__)


async def gossipmesh_exception_handler(request: Request, exc: GossipMeshException) -> JSONResponse:
    # Log the full exception with details, but be careful not to log sensitive details directly
    # from the request unless sanitized. For now, log the exception info.
    logger.error(f"GossipMeshException: {exc.error_code} - {exc.message} - Details: {exc.details}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                # We do not return exc.details to the client to avoid leaking sensitive data
            }
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the full exception stack trace for debugging
    logger.exception(f"Unhandled exception: {str(exc)}")

    # Do not expose internal error details to the client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
            }
        },
    )
