import asyncio
import httpx
import logging
import uuid
from datetime import datetime, timezone

from app.core.state import app_state
from app.services.webhook_dispatcher import dispatch_alert

logger = logging.getLogger("watchtower.monitor")

FAILURE_RATE_THRESHOLD = 0.20  # 20%


async def check_single_proxy(proxy_id: str, url: str, timeout: float) -> dict:
    """
    Attempt an HTTP GET on *url* to determine status.
    Timeouts and 5xx responses classify as 'down'.
    """
    try:
        async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout),
                follow_redirects=True,
                verify=False,
        ) as client:
            resp = await client.get(url)
            # 2xx is 'up', everything else is 'down'
            status = "up" if 200 <= resp.status_code < 300 else "down"
    except Exception as exc:
        logger.debug("Proxy %s unreachable: %s", url, exc)
        status = "down"

    return {"proxy_id": proxy_id, "status": status}


async def run_check_cycle():
    """Check all registered proxies concurrently, then evaluate alert rule."""
    if not app_state.proxies:
        return

    # Handle config variables (falling back to defaults if needed)
    timeout_ms = getattr(app_state, "proxy_timeout", 3000)
    if hasattr(app_state, "current_config"):
        timeout_ms = app_state.current_config.request_timeout_ms
    timeout_sec = timeout_ms / 1000.0

    # Execute concurrent checks using the proxy_id
    tasks = {pid: asyncio.create_task(check_single_proxy(pid, p_data["url"], timeout_sec))
             for pid, p_data in app_state.proxies.items()}

    results = {}
    for pid, task in tasks.items():
        results[pid] = await task

    now_iso = datetime.now(timezone.utc).isoformat()
    down_proxy_ids = []

    # Update in-memory state
    for pid, result in results.items():
        record = app_state.proxies[pid]
        record["status"] = result["status"]
        record["last_checked_at"] = now_iso

        if result["status"] == "down":
            record["consecutive_failures"] = record.get("consecutive_failures", 0) + 1
            down_proxy_ids.append(pid)
        else:
            record["consecutive_failures"] = 0

    total = len(app_state.proxies)
    down_count = len(down_proxy_ids)
    failure_rate = down_count / total if total > 0 else 0.0

    logger.info("Cycle complete — %d/%d down (%.0f%%)", down_count, total, failure_rate * 100)
    await evaluate_alert(total, down_count, failure_rate, down_proxy_ids, now_iso)


async def evaluate_alert(total: int, down_count: int, failure_rate: float, down_proxy_ids: list, now_iso: str):
    """Fire webhook alert if failure rate ≥ 20%. Resolve when it drops back."""

    # 1. BREACH DETECTED
    if failure_rate >= FAILURE_RATE_THRESHOLD:
        if getattr(app_state, "alert_active", False) is False:
            app_state.alert_active = True
            alert_id = f"alert-{uuid.uuid4().hex[:8]}"

            # This perfectly matches the Chapter 09 requirements
            alert_record = {
                "alert_id": alert_id,
                "status": "active",
                "failure_rate": round(failure_rate, 4),
                "total_proxies": total,
                "failed_proxies": down_count,
                "failed_proxy_ids": down_proxy_ids,
                "threshold": FAILURE_RATE_THRESHOLD,
                "fired_at": now_iso,
                "resolved_at": None,
                "message": "Proxy pool failure rate exceeded threshold"
            }

            if not hasattr(app_state, "alerts"):
                app_state.alerts = []
            app_state.alerts.append(alert_record)
            logger.warning("ALERT FIRED: %s", alert_id)

            # Dispatch 'alert.fired' webhook event payload (Chapter 10)
            payload = {"event": "alert.fired"}
            payload.update(alert_record)
            asyncio.create_task(dispatch_alert(payload))

    # 2. SYSTEM RECOVERED
    else:
        if getattr(app_state, "alert_active", False) is True:
            app_state.alert_active = False

            resolved_alert = None
            if hasattr(app_state, "alerts") and app_state.alerts:
                # Mark the active alert as resolved in the archive
                for a in reversed(app_state.alerts):
                    if a.get("status") == "active":
                        a["status"] = "resolved"
                        a["resolved_at"] = now_iso
                        resolved_alert = a
                        break

            logger.info("Alert resolved — failure rate back below threshold")

            if resolved_alert:
                # Dispatch 'alert.resolved' webhook event payload (Chapter 10)
                payload = {
                    "event": "alert.resolved",
                    "alert_id": resolved_alert["alert_id"],
                    "resolved_at": resolved_alert["resolved_at"]
                }
                asyncio.create_task(dispatch_alert(payload))


async def monitoring_loop():
    """
    Infinite background loop.
    """
    logger.info("Monitoring loop started.")
    while True:
        try:
            await run_check_cycle()
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled.")
            raise
        except Exception as exc:
            logger.exception("Unexpected error in monitoring loop: %s", exc)

        interval = getattr(app_state, "check_interval", 15)
        if hasattr(app_state, "current_config"):
            interval = app_state.current_config.check_interval_seconds

        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled during sleep.")
            raise