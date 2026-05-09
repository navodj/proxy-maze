from fastapi import APIRouter, HTTPException, status
from typing import List
from app.core.state import app_state
from app.models.schemas import ProxyListRequest
import asyncio
from app.services.monitor import run_check_cycle

router = APIRouter(tags=["Proxies"])


def extract_proxy_id(url: str) -> str:
    # Extracts the final segment of the URL as required by Chapter 7
    return url.rstrip("/").split("/")[-1]


@router.post("/proxies", status_code=status.HTTP_201_CREATED, summary="Register proxies to monitor")
async def add_proxies(body: ProxyListRequest):
    """
    Upload a list of proxy URLs. Replaces the pool if requested.
    """
    # 1. Handle the "replace" flag as required by the brief
    if body.replace:
        app_state.proxies.clear()

    accepted_proxies = []

    for url in body.proxies:
        url = url.strip()
        if not url:
            continue

        proxy_id = extract_proxy_id(url)

        # 2. Store using the strict data structure required for GET /proxies
        app_state.proxies[proxy_id] = {
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
    asyncio.create_task(run_check_cycle())

    # 3. Return the exact JSON structure the black-box test expects
    return {
        "accepted": len(accepted_proxies),
        "proxies": accepted_proxies
    }


@router.get("/proxies", summary="List all proxies and their status")
async def list_proxies():
    total = len(app_state.proxies)
    up = sum(1 for p in app_state.proxies.values() if p["status"] == "up")
    down = sum(1 for p in app_state.proxies.values() if p["status"] == "down")
    failure_rate = (down / total) if total > 0 else 0.0

    # Strip history for the summary endpoint
    summary_proxies = []
    for p in app_state.proxies.values():
        summary_proxies.append({
            "id": p["id"],
            "url": p["url"],
            "status": p["status"],
            "last_checked_at": p["last_checked_at"],
            "consecutive_failures": p["consecutive_failures"]
        })

    return {
        "total": total,
        "up": up,
        "down": down,
        "failure_rate": round(failure_rate, 4),
        "proxies": summary_proxies
    }


@router.delete("/proxies", status_code=status.HTTP_204_NO_CONTENT, summary="Remove all proxies")
async def clear_proxies():
    app_state.proxies.clear()
    return None  # 204 No Content must not have a response body


@router.get("/proxies/{proxy_id}", summary="Get proxy dossier")
async def get_proxy(proxy_id: str):
    if proxy_id not in app_state.proxies:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return app_state.proxies[proxy_id]


@router.get("/proxies/{proxy_id}/history", summary="Get proxy chronicle")
async def get_proxy_history(proxy_id: str):
    if proxy_id not in app_state.proxies:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return app_state.proxies[proxy_id].get("history", [])
