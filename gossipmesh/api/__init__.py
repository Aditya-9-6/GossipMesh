from fastapi import FastAPI
from .webhooks import router as webhooks_router

app = FastAPI(title="GossipMesh Webhook API", version="0.1.0")
app.include_router(webhooks_router)
