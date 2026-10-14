from fastapi import FastAPI

from gossipmesh.api.errors import global_exception_handler, gossipmesh_exception_handler
from gossipmesh.core.exceptions import GossipMeshException

from .webhooks import router as webhooks_router

app = FastAPI(title="GossipMesh Webhook API", version="0.1.0")
app.include_router(webhooks_router)
app.add_exception_handler(GossipMeshException, gossipmesh_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
