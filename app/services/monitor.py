import asyncio
import httpx
import logging
from datetime import datetime, timezone
from typing import Dict

from app.core.state import app_state
from app.services.webhook_dispatcher import dispatch_alert

logger = logging.getLogger("watchtower.monitor")

FAILURE_RATE_THRESHOLD = 0.20   # 20 %


async def check_single_proxy(url: str, timeout: int) -> dict:
    """
    Attempt an HTTP HEAD (fallback GET) on *url*.
    Returns a dict with status, response_time_ms.
    """
    start = asyncio.get_event_loop().time()
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            verify=False,          # proxies may use self-signed certs
        ) as client:
            resp = await client.head(url)
            elapsed = (asyncio.get_event_loop().time() - start) * 1000
            status = "up" if resp.status_code < 500 else "down"
            return {"status": status, "response_time_ms": round(elapsed, 2)}
    except Exception as exc:
        elapsed = (asyncio.get_event_loop().time() - start) * 1000
        logger.debug("Proxy %s unreachable: %s", url, exc)
        return {"status": "down", "response_time_ms": round(elapsed, 2)}


async def run_check_cycle():
    """Check all registered proxies concurrently, then evaluate alert rule."""
    if not app_state.proxies:
        return

    timeout = app_state.proxy_timeout
    urls = list(app_state.proxies.keys())

    tasks = {url: asyncio.create_task(check_single_proxy(url, timeout)) for url in urls}
    results: Dict[str, dict] = {}
    for url, task in tasks.items():
        results[url] = await task

    now = datetime.now(timezone.utc)
    down_urls = []

    for url, result in results.items():
        record = app_state.proxies[url]
        record["status"] = result["status"]
        record["last_checked"] = now.isoformat()
        record["response_time_ms"] = result["response_time_ms"]
        if result["status"] == "down":
            record["failure_count"] = record.get("failure_count", 0) + 1
            down_urls.append(url)
        else:
            record["failure_count"] = 0

    total = len(urls)
    down_count = len(down_urls)
    failure_rate = down_count / total if total > 0 else 0.0

    logger.info(
        "Cycle complete — %d/%d down (%.0f%%)", down_count, total, failure_rate * 100
    )

    await evaluate_alert(total, down_count, failure_rate, down_urls, now)


async def evaluate_alert(total, down_count, failure_rate, down_urls, now):
    """Fire webhook alert if failure rate ≥ 20 %. Resolve when it drops back."""
    if failure_rate >= FAILURE_RATE_THRESHOLD:
        if not app_state.alert_active:
            app_state.alert_active = True
            alert = build_alert_record(total, down_count, failure_rate, down_urls, now)
            app_state.alerts.append(alert)
            logger.warning(
                "ALERT triggered — failure rate %.0f%%", failure_rate * 100
            )
            await dispatch_alert(alert)
    else:
        if app_state.alert_active:
            app_state.alert_active = False
            # Mark last open alert as resolved
            for a in reversed(app_state.alerts):
                if a.get("resolved_at") is None:
                    a["resolved_at"] = now.isoformat()
                    break
            logger.info("Alert resolved — failure rate back below threshold")


def build_alert_record(total, down_count, failure_rate, down_urls, now) -> dict:
    import uuid
    return {
        "id": str(uuid.uuid4()),
        "triggered_at": now.isoformat(),
        "total_proxies": total,
        "down_proxies": down_count,
        "failure_rate": round(failure_rate, 4),
        "down_urls": down_urls,
        "resolved_at": None,
    }


async def monitoring_loop():
    """
    Infinite background loop.
    Runs check cycles separated by *check_interval* seconds.
    Safe to cancel via task.cancel().
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

        try:
            await asyncio.sleep(app_state.check_interval)
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled during sleep.")
            raise
