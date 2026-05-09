import httpx
import asyncio
import logging
import time
from app.core.state import app_state

logger = logging.getLogger("watchtower.webhooks")

async def send_with_retry(url: str, payload: dict):
    max_retries = 10
    base_delay = 1  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=5.0)

                if 200 <= resp.status_code < 300:
                    if not hasattr(app_state, "webhook_deliveries_counter"):
                        app_state.webhook_deliveries_counter = 0
                    app_state.webhook_deliveries_counter += 1
                    logger.info(f"✅ Webhook delivered successfully to {url}")
                    return

                if resp.status_code in [500, 502, 503, 504]:
                    logger.warning(f"⚠️ Transient error {resp.status_code} from {url}. Retrying...")
                else:
                    return  # 4xx error, do not retry

        except (httpx.RequestError, httpx.TimeoutException):
            logger.warning(f"⚠️ Connection error to {url}. Retrying...")

        if attempt < max_retries:
            await asyncio.sleep(base_delay * attempt)


def build_slack_payload(event_type: str, payload: dict, username: str) -> dict:
    if event_type == "alert.fired":
        return {
            "username": username,
            "text": payload.get("message", "Proxy pool failure rate exceeded threshold"),
            "attachments": [{
                "color": "#FF0000",
                "fields": [
                    {"title": "Alert ID", "value": payload["alert_id"]},
                    {"title": "Failure Rate", "value": str(payload["failure_rate"])},
                    {"title": "Failed Proxies", "value": str(payload["failed_proxies"])},
                    {"title": "Threshold", "value": str(payload["threshold"])},
                    {"title": "Failed IDs", "value": ", ".join(payload["failed_proxy_ids"])},
                    {"title": "Fired At", "value": payload["fired_at"]}
                ],
                "footer": "TorchProxies Watchtower",
                "ts": int(time.time())
            }]
        }
    else:
        return {
            "username": username,
            "text": "Alert Resolved",
            "attachments": [{
                "color": "#00FF00",
                "fields": [
                    {"title": "Alert ID", "value": payload["alert_id"]},
                ],
                "footer": "TorchProxies Watchtower",
                "ts": int(time.time())
            }]
        }


def build_discord_payload(event_type: str, payload: dict, username: str) -> dict:
    if event_type == "alert.fired":
        return {
            "username": username,
            "embeds": [{
                "title": "Alert Fired",
                "description": payload.get("message", "Proxy breach detected"),
                "color": 16711680,
                "fields": [
                    {"name": "Alert ID", "value": payload["alert_id"]},
                    {"name": "Failure Rate", "value": str(payload["failure_rate"])},
                    {"name": "Failed Proxies", "value": str(payload["failed_proxies"])},
                    {"name": "Threshold", "value": str(payload["threshold"])},
                    {"name": "Failed IDs", "value": ", ".join(payload["failed_proxy_ids"])}
                ],
                "footer": {"text": "TorchProxies Watchtower"}
            }]
        }
    else:
        return {
            "username": username,
            "embeds": [{
                "title": "Alert Resolved",
                "description": "The pool has recovered.",
                "color": 65280,
                "fields": [
                    {"name": "Alert ID", "value": payload["alert_id"]}
                ],
                "footer": {"text": "TorchProxies Watchtower"}
            }]
        }


async def dispatch_alert(payload: dict, event_type: str):
    tasks = []

    # 1. Generic Webhooks (Chapter 10)
    if hasattr(app_state, "webhooks") and app_state.webhooks:
        for url in app_state.webhooks:
            tasks.append(send_with_retry(url, payload))

    # 2. Slack and Discord Integrations (Chapter 11)
    if hasattr(app_state, "integrations") and app_state.integrations:
        for integ in app_state.integrations:
            if event_type in integ["events"]:
                if integ["type"] == "slack":
                    slack_payload = build_slack_payload(event_type, payload, integ["username"])
                    tasks.append(send_with_retry(integ["webhook_url"], slack_payload))
                elif integ["type"] == "discord":
                    discord_payload = build_discord_payload(event_type, payload, integ["username"])
                    tasks.append(send_with_retry(integ["webhook_url"], discord_payload))

    if tasks:
        await asyncio.gather(*tasks)