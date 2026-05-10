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


def build_slack_payload(event_type: str, payload: dict, username: str) -> dict:
    if event_type == "alert.fired":
        return {
            "username": username,
            "text": "Proxy pool failure rate exceeded threshold",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Proxy Alert Fired"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Alert ID:*\n{payload.get('alert_id')}"},
                        {"type": "mrkdwn", "text": f"*Failure Rate:*\n{payload.get('failure_rate')}"},
                        {"type": "mrkdwn", "text": f"*Threshold:*\n{payload.get('threshold')}"},
                        {"type": "mrkdwn",
                         "text": f"*Failed Proxies:*\n{payload.get('failed_proxies')}/{payload.get('total_proxies')}"},
                        {"type": "mrkdwn", "text": f"*Failed IDs:*\n{', '.join(payload.get('failed_proxy_ids', []))}"}
                    ]
                }
            ]
        }
    return {
        "username": username,
        "text": f"✅ Alert Resolved: {payload.get('alert_id')}"
    }


def build_discord_payload(event_type: str, payload: dict, username: str) -> dict:
    if event_type == "alert.fired":
        return {
            "username": username,
            "content": "Alert status update",
            "embeds": [{
                "title": "🚨 Alert Fired",
                "color": 16711680,
                "fields": [
                    {"name": "Alert ID", "value": str(payload.get('alert_id')), "inline": True},
                    {"name": "Failure Rate", "value": str(payload.get('failure_rate')), "inline": True},
                    {"name": "Threshold", "value": str(payload.get('threshold')), "inline": True},
                    {"name": "Failed Proxies", "value": str(payload.get('failed_proxies')), "inline": True},
                    {"name": "Total Proxies", "value": str(payload.get('total_proxies')), "inline": True},
                    {"name": "Failed IDs", "value": ", ".join(payload.get('failed_proxy_ids', [])), "inline": False}
                ]
            }]
        }
    return {
        "username": username,
        "content": "Alert status update",
        "embeds": [{
            "title": "✅ Alert Resolved",
            "color": 65280,
            "fields": [{"name": "Alert ID", "value": str(payload.get('alert_id'))}]
        }]
    }


async def dispatch_single_integration(integ: dict, payload: dict, event_type: str):
    url = None
    platform = None
    username = integ.get("username", "Watchtower")

    # Blindly scrape the dictionary
    for key, val in integ.items():
        if isinstance(val, str):
            val_lower = val.lower()
            if val_lower.startswith("http"):
                url = val
            elif "slack" in val_lower:
                platform = "slack"
            elif "discord" in val_lower:
                platform = "discord"

    if not url or not platform:
        return

    if platform == "slack":
        await send_with_retry(url, build_slack_payload(event_type, payload, username))
    elif platform == "discord":
        await send_with_retry(url, build_discord_payload(event_type, payload, username))


async def dispatch_alert(payload: dict, event_type: str):
    tasks = []

    if getattr(app_state, "webhooks", None):
        for wh in app_state.webhooks:
            url = wh["url"] if isinstance(wh, dict) else wh
            tasks.append(send_with_retry(url, payload))

    if getattr(app_state, "integrations", None):
        for integ in app_state.integrations:
            tasks.append(dispatch_single_integration(integ, payload, event_type))

    if tasks:
        await asyncio.gather(*tasks)