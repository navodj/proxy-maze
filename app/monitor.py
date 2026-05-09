import asyncio
import httpx
import uuid
from datetime import datetime, timezone
from app import state
from app.webhooks import dispatch_all_webhooks


async def check_single_proxy(proxy_id: str, url: str):
    timeout_seconds = state.current_config.request_timeout_ms / 1000.0

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url)
            status = "up" if 200 <= response.status_code < 300 else "down"
    except (httpx.RequestError, httpx.TimeoutException):
        status = "down"

    now_iso = datetime.now(timezone.utc).isoformat()
    proxy = state.proxy_pool[proxy_id]

    # Update live status
    proxy["status"] = status
    proxy["last_checked_at"] = now_iso
    proxy["total_checks"] = proxy.get("total_checks", 0) + 1

    if status == "down":
        proxy["consecutive_failures"] += 1
    else:
        proxy["consecutive_failures"] = 0

    # Maintain history for GET /proxies/{id}/history
    if "history" not in proxy:
        proxy["history"] = []
    proxy["history"].append({"checked_at": now_iso, "status": status})

    # Calculate uptime percentage
    up_count = sum(1 for h in proxy["history"] if h["status"] == "up")
    proxy["uptime_percentage"] = round((up_count / proxy["total_checks"]) * 100, 1)

    state.total_checks_counter += 1


async def monitoring_loop():
    while True:
        # 1. Ping the pool
        tasks = [check_single_proxy(pid, p["url"]) for pid, p in state.proxy_pool.items()]
        if tasks:
            await asyncio.gather(*tasks)

        # 2. Compute metrics
        total = len(state.proxy_pool)
        down_proxies = [p for p in state.proxy_pool.values() if p["status"] == "down"]
        down_count = len(down_proxies)
        failure_rate = (down_count / total) if total > 0 else 0.0

        # 3. Alert Lifecycle
        if failure_rate >= 0.20 and state.current_active_alert is None:
            alert_id = f"alert-{uuid.uuid4().hex[:8]}"
            state.current_active_alert = {
                "alert_id": alert_id,
                "status": "active",
                "failure_rate": round(failure_rate, 4),
                "total_proxies": total,
                "failed_proxies": down_count,
                "failed_proxy_ids": [p["id"] for p in down_proxies],
                "threshold": 0.20,
                "fired_at": datetime.now(timezone.utc).isoformat(),
                "resolved_at": None,
                "message": "Proxy pool failure rate exceeded threshold"
            }
            state.alert_archive.append(state.current_active_alert)
            asyncio.create_task(dispatch_all_webhooks("alert.fired", state.current_active_alert))

        elif failure_rate < 0.20 and state.current_active_alert is not None:
            state.current_active_alert["status"] = "resolved"
            state.current_active_alert["resolved_at"] = datetime.now(timezone.utc).isoformat()
            resolved_alert_data = state.current_active_alert.copy()
            state.current_active_alert = None
            asyncio.create_task(dispatch_all_webhooks("alert.resolved", resolved_alert_data))

        await asyncio.sleep(state.current_config.check_interval_seconds)