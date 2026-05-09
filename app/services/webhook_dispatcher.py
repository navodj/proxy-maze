import httpx
import asyncio
import logging
from app.core.state import app_state

logger = logging.getLogger("watchtower.webhooks")


MAX_RETRIES = 10
REQUEST_TIMEOUT_SECONDS = 5.0


def build_payload_for_platform(platform: str, alert_payload: dict) -> dict:
    normalized = (platform or "generic").lower()
    if normalized == "slack":
        event = alert_payload.get("event", "alert.fired")
        title = "Watchtower Alert Fired" if event == "alert.fired" else "Watchtower Alert Resolved"
        fields = []
        if "alert_id" in alert_payload:
            fields.append({"type": "mrkdwn", "text": f"*Alert ID:*\n`{alert_payload['alert_id']}`"})
        if "failure_rate" in alert_payload:
            fields.append({"type": "mrkdwn", "text": f"*Failure Rate:*\n{round(float(alert_payload['failure_rate']) * 100, 1)}%"})
        if "failed_proxies" in alert_payload and "total_proxies" in alert_payload:
            fields.append({"type": "mrkdwn", "text": f"*Down / Total:*\n{alert_payload['failed_proxies']} / {alert_payload['total_proxies']}"})
        if "fired_at" in alert_payload:
            fields.append({"type": "mrkdwn", "text": f"*Fired At:*\n{alert_payload['fired_at']}"})
        if "resolved_at" in alert_payload and alert_payload["resolved_at"] is not None:
            fields.append({"type": "mrkdwn", "text": f"*Resolved At:*\n{alert_payload['resolved_at']}"})

        if not fields:
            fields.append({"type": "mrkdwn", "text": f"```{alert_payload}```"})

        return {
            "text": title,
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": title},
                },
                {
                    "type": "section",
                    "fields": fields,
                },
            ],
        }

    if normalized == "discord":
        event = alert_payload.get("event", "alert.fired")
        title = "Watchtower Alert Fired" if event == "alert.fired" else "Watchtower Alert Resolved"
        color = 0xE01E5A if event == "alert.fired" else 0x2EB67D
        embed_fields = []
        if "alert_id" in alert_payload:
            embed_fields.append({"name": "Alert ID", "value": str(alert_payload["alert_id"]), "inline": False})
        if "failure_rate" in alert_payload:
            embed_fields.append({"name": "Failure Rate", "value": f"{round(float(alert_payload['failure_rate']) * 100, 1)}%", "inline": True})
        if "failed_proxies" in alert_payload and "total_proxies" in alert_payload:
            embed_fields.append({"name": "Down / Total", "value": f"{alert_payload['failed_proxies']} / {alert_payload['total_proxies']}", "inline": True})
        if "fired_at" in alert_payload:
            embed_fields.append({"name": "Fired At", "value": str(alert_payload["fired_at"]), "inline": False})
        if "resolved_at" in alert_payload and alert_payload["resolved_at"] is not None:
            embed_fields.append({"name": "Resolved At", "value": str(alert_payload["resolved_at"]), "inline": False})

        return {
            "content": title,
            "embeds": [
                {
                    "title": title,
                    "description": alert_payload.get("message", "Watchtower proxy monitoring event"),
                    "color": color,
                    "fields": embed_fields,
                }
            ],
        }

    return alert_payload


async def send_with_retry(webhook: dict | str, alert_payload: dict):
    if isinstance(webhook, dict):
        url = webhook["url"]
        platform = webhook.get("platform", "generic")
        secret = webhook.get("secret")
    else:
        url = webhook
        platform = "generic"
        secret = None

    payload = build_payload_for_platform(platform, alert_payload)
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Webhook-Secret"] = secret

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT_SECONDS,
                follow_redirects=True,
                verify=False,
            ) as client:
                resp = await client.post(url, json=payload, headers=headers)

                if 200 <= resp.status_code < 300:
                    app_state.webhook_deliveries_counter += 1
                    logger.info(f"✅ Webhook delivered successfully to {url}")
                    return

                # Retry strictly on 5xx transient errors
                if resp.status_code in [500, 502, 503, 504]:
                    logger.warning(f"⚠️ Transient error {resp.status_code} from {url}. Retrying...")
                else:
                    return  # 4xx error, do not retry

        except (httpx.RequestError, httpx.TimeoutException):
            logger.warning(f"⚠️ Connection error to {url}. Retrying...")

        if attempt < MAX_RETRIES:
            await asyncio.sleep(min(2 ** (attempt - 1), 8))


async def dispatch_alert(payload: dict):
    if not app_state.webhooks:
        return

    # Dispatch to all registered capture URLs concurrently
    tasks = [send_with_retry(webhook, payload) for webhook in app_state.webhooks]
    await asyncio.gather(*tasks)
