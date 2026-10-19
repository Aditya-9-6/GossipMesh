from fastapi import APIRouter
from .webhooks import router as webhooks_router

router = APIRouter()
router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
