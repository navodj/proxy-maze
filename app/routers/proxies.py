from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from typing import List

from app.core.state import app_state
from app.models.schemas import ProxyListRequest
from app.services.monitor import run_check_cycle

router = APIRouter(tags=["Proxies"])


@router.post("/proxies", summary="Register proxies to monitor")
async def add_proxies(body: ProxyListRequest):
    """
    Upload a list of proxy URLs. Duplicate URLs are ignored.
    An immediate background check cycle is triggered right away.
    """
    added = []
    skipped = []
    for url in body.proxies:
        url = url.strip()
        if not url:
            continue
        if url in app_state.proxies:
            skipped.append(url)
        else:
            app_state.proxies[url] = {
                "url": url,
                "status": "unknown",
                "last_checked": None,
                "response_time_ms": None,
                "failure_count": 0,
                "added_at": datetime.now(timezone.utc).isoformat(),
            }
            added.append(url)

    # Fire an immediate check cycle (non-blocking)
    import asyncio
    asyncio.create_task(run_check_cycle())

    return {
        "message": f"Added {len(added)} proxies. {len(skipped)} already existed.",
        "added": added,
        "skipped": skipped,
        "total_monitored": len(app_state.proxies),
    }


@router.get("/proxies", summary="List all proxies and their status")
async def list_proxies():
    proxies = list(app_state.proxies.values())
    total = len(proxies)
    up = sum(1 for p in proxies if p["status"] == "up")
    down = sum(1 for p in proxies if p["status"] == "down")
    failure_rate = round(down / total, 4) if total else 0.0

    return {
        "total": total,
        "up": up,
        "down": down,
        "failure_rate_pct": round(failure_rate * 100, 1),
        "alert_active": app_state.alert_active,
        "proxies": proxies,
    }


@router.delete("/proxies", summary="Remove all proxies")
async def clear_proxies():
    count = len(app_state.proxies)
    app_state.proxies.clear()
    app_state.alert_active = False
    return {"message": f"Cleared {count} proxies."}


@router.delete("/proxies/{proxy_url:path}", summary="Remove a specific proxy")
async def delete_proxy(proxy_url: str):
    if proxy_url not in app_state.proxies:
        raise HTTPException(404, f"Proxy '{proxy_url}' not found.")
    del app_state.proxies[proxy_url]
    return {"message": f"Removed proxy: {proxy_url}"}


@router.post("/proxies/check", summary="Trigger an immediate check cycle")
async def trigger_check():
    import asyncio
    asyncio.create_task(run_check_cycle())
    return {"message": "Check cycle triggered."}
