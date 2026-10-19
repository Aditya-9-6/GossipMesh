from fastapi import FastAPI, APIRouter
from .webhooks import router as webhooks_router
from gossipmesh.api.routers.approvals import router as approvals_router
from gossipmesh.api.errors import gossipmesh_exception_handler, global_exception_handler
from gossipmesh.core.exceptions import GossipMeshException

app = FastAPI(title="GossipMesh Webhook API", version="0.1.0")
app.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
app.include_router(approvals_router)
app.add_exception_handler(GossipMeshException, gossipmesh_exception_handler) # type: ignore
app.add_exception_handler(Exception, global_exception_handler) # type: ignore

router = APIRouter()
router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
