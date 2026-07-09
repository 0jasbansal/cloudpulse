from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
import os
import time

app = FastAPI(title="CloudPulse API")

# Prometheus metrics exposed at /metrics automatically
Instrumentator().instrument(app).expose(app)

START_TIME = time.time()

# In-memory "database" so the app works even before you wire up Postgres.
# Swap this for real SQLAlchemy + Postgres once the pipeline is working end-to-end.
ITEMS = {}
NEXT_ID = 1


class Item(BaseModel):
    name: str
    description: str = ""


@app.get("/")
def root():
    return {"service": "CloudPulse API", "status": "running"}


@app.get("/health")
def health():
    """
    Used by Kubernetes liveness/readiness probes AND by ArgoCD/monitoring
    to decide if a deployment is healthy. If this ever returns non-200,
    Kubernetes will restart the pod and (if configured) roll back the release.
    """
    return {
        "status": "healthy",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "version": os.getenv("APP_VERSION", "dev"),
    }


@app.get("/items")
def list_items():
    return list(ITEMS.values())


@app.post("/items")
def create_item(item: Item):
    global NEXT_ID
    ITEMS[NEXT_ID] = {"id": NEXT_ID, **item.model_dump()}
    NEXT_ID += 1
    return ITEMS[NEXT_ID - 1]


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    return ITEMS[item_id]
