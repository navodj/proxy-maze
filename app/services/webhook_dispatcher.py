import httpx
import asyncio
import logging
from app.core.state import app_state

logger = logging.getLogger("watchtower.webhooks")


async def send_with_retry(url: str, payload: dict):
    max_retries = 10
    base_delay = 1

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.post(url, json=payload, timeout=5.0)

                if 200 <= resp.status_code < 300:
                    app_state.webhook_deliveries_counter = getattr(app_state, "webhook_deliveries_counter", 0) + 1
                    logger.info(f"✅ Webhook delivered successfully to {url}")
                    return

                # Handle the redirects manually
                if resp.status_code in [301, 302, 307, 308]:
                    redirect_url = resp.headers.get("location")
                    if redirect_url:
                        url = redirect_url
                        continue

                if resp.status_code in [500, 502, 503, 504]:
                    logger.warning(f"⚠️ Transient error {resp.status_code} from {url}. Retrying...")
                else:
                    logger.error(f"❌ Rejected by Capture Server (Status: {resp.status_code}). Payload dropped.")
                    return

        except (httpx.RequestError, httpx.TimeoutException):
            logger.warning(f"⚠️ Connection error to {url}. Retrying...")

        if attempt < max_retries:
            await asyncio.sleep(base_delay)


def build_slack_payload(event_type: str, payload: dict) -> dict:
    if event_type == "alert.fired":
        return {
            "text": "Proxy pool failure rate exceeded threshold",
            "blocks": [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚨 *Alert Fired*\n*ID:* {payload['alert_id']}\n*Rate:* {payload['failure_rate']}\n*Failed IDs:* {', '.join(payload['failed_proxy_ids'])}"
                }
            }]
        }
    return {"text": f"✅ Alert Resolved: {payload['alert_id']}"}


def build_discord_payload(event_type: str, payload: dict) -> dict:
    if event_type == "alert.fired":
        return {
            "embeds": [{
                "title": "🚨 Alert Fired",
                "color": 16711680,
                "fields": [
                    {"name": "Alert ID", "value": payload["alert_id"]},
                    {"name": "Failure Rate", "value": str(payload["failure_rate"])},
                    {"name": "Failed IDs", "value": ", ".join(payload["failed_proxy_ids"])}
                ]
            }]
        }
    return {
        "embeds": [{
            "title": "✅ Alert Resolved",
            "color": 65280,
            "fields": [{"name": "Alert ID", "value": payload["alert_id"]}]
        }]
    }


async def dispatch_alert(payload: dict, event_type: str):
    tasks = []

    # 1. Standard Webhooks
    if getattr(app_state, "webhooks", None):
        for wh in app_state.webhooks:
            url = wh["url"] if isinstance(wh, dict) else wh
            tasks.append(send_with_retry(url, payload))

    # 2. Slack & Discord Integrations (Filter Removed!)
    if getattr(app_state, "integrations", None):
        for integ in app_state.integrations:
            # Safely grab the URL whether it's named webhook_url or url
            url = integ.get("webhook_url") or integ.get("url")
            platform = integ.get("type", "").lower()

            if not url:
                continue

            if platform == "slack":
                tasks.append(send_with_retry(url, build_slack_payload(event_type, payload)))
            elif platform == "discord":
                tasks.append(send_with_retry(url, build_discord_payload(event_type, payload)))

    if tasks:
        await asyncio.gather(*tasks)