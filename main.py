import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers import health, config, proxies, alerts, webhooks, integrations
from app.core.state import app_state
from app.services.monitor import monitoring_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background monitoring loop on startup."""
    task = asyncio.create_task(monitoring_loop())
    app_state.monitor_task = task
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Watchtower – Proxy Monitor",
    description="Real-time proxy health monitoring with webhook alerting.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(config.router)
app.include_router(proxies.router)
app.include_router(alerts.router)
app.include_router(webhooks.router)
app.include_router(integrations.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
