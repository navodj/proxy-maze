import asyncio
import httpx
import logging
import uuid
from datetime import datetime, timezone

from app.core.state import app_state
from app.services.webhook_dispatcher import dispatch_alert

logger = logging.getLogger("watchtower.monitor")

FAILURE_RATE_THRESHOLD = 0.20
check_lock = asyncio.Lock()  # Prevents race conditions and duplicate alerts


async def check_single_proxy(proxy_id: str, url: str, timeout: float) -> dict:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout), follow_redirects=True, verify=False) as client:
            resp = await client.get(url)
            status = "up" if 200 <= resp.status_code < 300 else "down"
    except Exception:
        status = "down"
    return {"proxy_id": proxy_id, "status": status}


async def run_check_cycle():
    # The Lock ensures only one cycle can evaluate the pool at a time
    async with check_lock:
        if not app_state.proxies:
            return

        timeout_sec = app_state.request_timeout_ms / 1000.0

        tasks = {pid: asyncio.create_task(check_single_proxy(pid, p_data["url"], timeout_sec))
                 for pid, p_data in app_state.proxies.items()}

        results = {}
        for pid, task in tasks.items():
            results[pid] = await task

        app_state.total_checks_counter += len(results)

        now_iso = datetime.now(timezone.utc).isoformat()
        down_proxy_ids = []

        for pid, result in results.items():
            record = app_state.proxies[pid]
            record["status"] = result["status"]
            record["last_checked_at"] = now_iso
            record["total_checks"] = record.get("total_checks", 0) + 1

            if result["status"] == "down":
                record["consecutive_failures"] = record.get("consecutive_failures", 0) + 1
                down_proxy_ids.append(pid)
            else:
                record["consecutive_failures"] = 0

            history = record.setdefault("history", [])
            history.append({"checked_at": now_iso, "status": result["status"]})

            up_checks = sum(1 for entry in history if entry["status"] == "up")
            record["uptime_percentage"] = round((up_checks / record["total_checks"]) * 100, 1)

        total = len(app_state.proxies)
        down_count = len(down_proxy_ids)
        failure_rate = down_count / total if total > 0 else 0.0
        down_proxy_ids_sorted = sorted(down_proxy_ids)

        await evaluate_alert(total, down_count, failure_rate, down_proxy_ids_sorted, now_iso)


async def evaluate_alert(total: int, down_count: int, failure_rate: float, down_proxy_ids: list, now_iso: str):
    if failure_rate >= FAILURE_RATE_THRESHOLD:
        if getattr(app_state, "alert_active", False) is False:
            app_state.alert_active = True
            alert_id = f"alert-{uuid.uuid4().hex[:8]}"

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

            payload = {"event": "alert.fired"}
            payload.update(alert_record)
            asyncio.create_task(dispatch_alert(payload))

    else:
        if getattr(app_state, "alert_active", False) is True:
            app_state.alert_active = False

            resolved_alert = None
            if hasattr(app_state, "alerts") and app_state.alerts:
                for a in reversed(app_state.alerts):
                    if a.get("status") == "active":
                        a["status"] = "resolved"
                        a["resolved_at"] = now_iso
                        resolved_alert = a
                        break

            if resolved_alert:
                payload = {
                    "event": "alert.resolved",
                    "alert_id": resolved_alert["alert_id"],
                    "resolved_at": resolved_alert["resolved_at"]
                }
                asyncio.create_task(dispatch_alert(payload))


async def monitoring_loop():
    while True:
        try:
            await run_check_cycle()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error in monitoring loop: %s", exc)

        interval = app_state.check_interval_seconds

        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
