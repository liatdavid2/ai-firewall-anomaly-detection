from fastapi import FastAPI
from app.api.connections import router as connections_router
from app.api.policies import router as policies_router
from app.services.ai_gateway import start_background_workers

app = FastAPI(
    title="AI Firewall",
    version="1.1.0",
    description="AI-driven firewall with policy evaluation and anomaly detection"
)

app.include_router(connections_router)
app.include_router(policies_router)

@app.on_event("startup")
def _startup() -> None:
    start_background_workers()
