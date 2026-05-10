from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone
from app.core.state import app_state
from app.models.schemas import ProxyListRequest
import asyncio
from app.services.monitor import run_check_cycle

router = APIRouter(tags=["Proxies"])


def extract_proxy_id(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def resolve_stale_alerts():
    if getattr(app_state, "alert_active", False):
        app_state.alert_active = False
        now_iso = datetime.now(timezone.utc).isoformat()
        if hasattr(app_state, "alerts"):
            for a in reversed(app_state.alerts):
                if a.get("status") == "active":
                    a["status"] = "resolved"
                    a["resolved_at"] = now_iso
                    break


@router.post("/proxies", status_code=status.HTTP_201_CREATED, summary="Register proxies to monitor")
async def add_proxies(body: ProxyListRequest):
    is_replace = getattr(body, "replace", False)
    # Check if the pool is currently empty (e.g., right after a DELETE)
    is_empty = len(getattr(app_state, "proxies", {})) == 0

    if is_replace:
        app_state.proxies.clear()

    # CRITICAL FIX: Always start fresh if replacing OR if adding to an empty pool!
    if is_replace or is_empty:
        resolve_stale_alerts()

    accepted_proxies = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Initialize the proxies dict if it doesn't exist
    if not hasattr(app_state, "proxies"):
        app_state.proxies = {}

    for url in body.proxies:
        url = url.strip()
        if not url:
            continue

        proxy_id = extract_proxy_id(url)
        app_state.proxies[proxy_id] = {
            "id": proxy_id,
            "url": url,
            "status": "pending",
            "last_checked_at": None,
            "response_time_ms": None,
            "consecutive_failures": 0,
            "total_checks": 0,
            "uptime_percentage": 0.0,
            "history": [],
            "added_at": now_iso
        }
        accepted_proxies.append({
            "id": proxy_id,
            "url": url,
            "status": "pending"
        })

    asyncio.create_task(run_check_cycle())

    return {
        "accepted": len(accepted_proxies),
        "proxies": accepted_proxies
    }


@router.get("/proxies", summary="List all proxies and their status")
async def list_proxies():
    proxies_list = list(getattr(app_state, "proxies", {}).values())
    total = len(proxies_list)
    up = sum(1 for p in proxies_list if p["status"] == "up")
    down = sum(1 for p in proxies_list if p["status"] == "down")
    failure_rate = (down / total) if total > 0 else 0.0

    return {
        "total": total,
        "up": up,
        "down": down,
        "failure_rate": round(failure_rate, 4),
        "proxies": proxies_list
    }


@router.delete("/proxies", status_code=status.HTTP_204_NO_CONTENT, summary="Remove all proxies")
async def clear_proxies():
    if hasattr(app_state, "proxies"):
        app_state.proxies.clear()
    return None


@router.get("/proxies/{proxy_id}", summary="Get proxy dossier")
async def get_proxy(proxy_id: str):
    if not hasattr(app_state, "proxies") or proxy_id not in app_state.proxies:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return app_state.proxies[proxy_id]


@router.get("/proxies/{proxy_id}/history", summary="Get proxy chronicle")
async def get_proxy_history(proxy_id: str):
    if not hasattr(app_state, "proxies") or proxy_id not in app_state.proxies:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return app_state.proxies[proxy_id].get("history", [])


@router.get("/metrics", summary="Get system metrics")
async def get_metrics():
    total = len(app_state.proxies) if hasattr(app_state, "proxies") else 0
    up = sum(1 for p in app_state.proxies.values() if p["status"] == "up") if total > 0 else 0
    down = total - up
    return {
        "total_proxies": total,
        "up_proxies": up,
        "down_proxies": down
    }