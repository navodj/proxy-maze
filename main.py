import asyncio
import uuid
from fastapi import FastAPI, HTTPException, Response
from app.models import Config, ProxyPayload, WebhookPayload
from app import state
from app.monitor import monitoring_loop

app = FastAPI(title="Torch Labs Watchtower")


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitoring_loop())


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/config")
async def set_config(config: Config):
    state.current_config = config
    return state.current_config


@app.get("/config")
async def get_config():
    return state.current_config


def extract_proxy_id(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


@app.post("/proxies", status_code=201)
async def load_proxies(payload: ProxyPayload):
    if payload.replace:
        state.proxy_pool.clear()

    accepted_proxies = []
    for url in payload.proxies:
        proxy_id = extract_proxy_id(url)
        state.proxy_pool[proxy_id] = {
            "id": proxy_id,
            "url": url,
            "status": "pending",
            "last_checked_at": None,
            "consecutive_failures": 0,
            "total_checks": 0,
            "uptime_percentage": 0.0,
            "history": []
        }
        accepted_proxies.append({
            "id": proxy_id,
            "url": url,
            "status": "pending"
        })
    return {"accepted": len(accepted_proxies), "proxies": accepted_proxies}


@app.get("/proxies")
async def get_pool_summary():
    total = len(state.proxy_pool)
    up_count = sum(1 for p in state.proxy_pool.values() if p["status"] == "up")
    down_count = sum(1 for p in state.proxy_pool.values() if p["status"] == "down")
    failure_rate = (down_count / total) if total > 0 else 0.0

    # Strip history for the summary endpoint
    summary_proxies = []
    for p in state.proxy_pool.values():
        summary_proxies.append({
            "id": p["id"],
            "url": p["url"],
            "status": p["status"],
            "last_checked_at": p["last_checked_at"],
            "consecutive_failures": p["consecutive_failures"]
        })

    return {
        "total": total,
        "up": up_count,
        "down": down_count,
        "failure_rate": round(failure_rate, 4),
        "proxies": summary_proxies
    }


@app.get("/proxies/{proxy_id}")
async def get_proxy_dossier(proxy_id: str):
    if proxy_id not in state.proxy_pool:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return state.proxy_pool[proxy_id]


@app.get("/proxies/{proxy_id}/history")
async def get_proxy_chronicle(proxy_id: str):
    if proxy_id not in state.proxy_pool:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return state.proxy_pool[proxy_id].get("history", [])


@app.delete("/proxies", status_code=204)
async def clear_graveyard():
    state.proxy_pool.clear()
    return Response(status_code=204)


@app.get("/alerts")
async def get_alerts():
    return state.alert_archive


@app.post("/webhooks", status_code=201)
async def register_webhook(payload: WebhookPayload):
    webhook_id = f"wh-{uuid.uuid4().hex[:6]}"
    if payload.url not in state.registered_webhooks:
        state.registered_webhooks.append(payload.url)
    return {"webhook_id": webhook_id, "url": payload.url}


@app.get("/metrics")
async def get_metrics():
    return {
        "total_checks": state.total_checks_counter,
        "current_pool_size": len(state.proxy_pool),
        "active_alerts": 1 if state.current_active_alert else 0,
        "total_alerts": len(state.alert_archive),
        "webhook_deliveries": state.webhook_deliveries_counter
    }