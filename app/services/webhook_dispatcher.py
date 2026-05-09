import asyncio
import httpx
import logging
from datetime import datetime

from app.core.state import app_state

logger = logging.getLogger("watchtower.webhook")

MAX_RETRIES = 10
BASE_BACKOFF = 2      # seconds — exponential back-off base
MAX_BACKOFF = 120     # cap at 2 minutes


def build_generic_payload(alert: dict) -> dict:
    """Standard JSON payload for generic webhooks."""
    return {
        "event": "proxy_alert",
        "alert_id": alert["id"],
        "triggered_at": alert["triggered_at"],
        "total_proxies": alert["total_proxies"],
        "down_proxies": alert["down_proxies"],
        "failure_rate_pct": round(alert["failure_rate"] * 100, 1),
        "down_urls": alert["down_urls"],
        "message": (
            f"🚨 Watchtower Alert — {alert['down_proxies']}/{alert['total_proxies']} "
            f"proxies are DOWN ({round(alert['failure_rate']*100,1)}% failure rate)."
        ),
    }


def build_slack_payload(alert: dict) -> dict:
    """Slack Block Kit formatted payload."""
    rate_pct = round(alert["failure_rate"] * 100, 1)
    down_list = "\n".join(f"• `{u}`" for u in alert["down_urls"][:10])
    if len(alert["down_urls"]) > 10:
        down_list += f"\n…and {len(alert['down_urls']) - 10} more"

    return {
        "text": f":rotating_light: Watchtower Alert — {rate_pct}% failure rate",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 Watchtower Proxy Alert"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Failure Rate:*\n{rate_pct}%"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Down / Total:*\n{alert['down_proxies']} / {alert['total_proxies']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Alert ID:*\n`{alert['id']}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{alert['triggered_at']}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Affected Proxies:*\n{down_list}"},
            },
            {"type": "divider"},
        ],
    }


def build_discord_payload(alert: dict) -> dict:
    """Discord Webhook embed payload."""
    rate_pct = round(alert["failure_rate"] * 100, 1)
    down_list = "\n".join(f"• `{u}`" for u in alert["down_urls"][:10])
    if len(alert["down_urls"]) > 10:
        down_list += f"\n…and {len(alert['down_urls']) - 10} more"

    return {
        "content": f"🚨 **Watchtower Alert** — {rate_pct}% failure rate",
        "embeds": [
            {
                "title": "Proxy Health Alert",
                "color": 0xFF0000,
                "fields": [
                    {"name": "Failure Rate", "value": f"{rate_pct}%", "inline": True},
                    {
                        "name": "Down / Total",
                        "value": f"{alert['down_proxies']} / {alert['total_proxies']}",
                        "inline": True,
                    },
                    {"name": "Alert ID", "value": f"`{alert['id']}`", "inline": False},
                    {
                        "name": "Affected Proxies",
                        "value": down_list or "None",
                        "inline": False,
                    },
                ],
                "timestamp": alert["triggered_at"],
                "footer": {"text": "Watchtower Proxy Monitor"},
            }
        ],
    }


def get_payload(webhook: dict, alert: dict) -> dict:
    platform = (webhook.get("platform") or "generic").lower()
    if platform == "slack":
        return build_slack_payload(alert)
    if platform == "discord":
        return build_discord_payload(alert)
    return build_generic_payload(alert)


async def send_with_retry(webhook: dict, payload: dict):
    """POST *payload* to *webhook['url']* with exponential back-off retries."""
    url = webhook["url"]
    headers = {"Content-Type": "application/json"}
    if webhook.get("secret"):
        headers["X-Webhook-Secret"] = webhook["secret"]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code < 500:
                    logger.info(
                        "Webhook delivered to %s (attempt %d, status %d)",
                        url, attempt, resp.status_code,
                    )
                    return
                logger.warning(
                    "Webhook %s returned %d on attempt %d — retrying",
                    url, resp.status_code, attempt,
                )
        except Exception as exc:
            logger.warning("Webhook %s failed on attempt %d: %s", url, attempt, exc)

        backoff = min(BASE_BACKOFF ** attempt, MAX_BACKOFF)
        logger.info("Retrying webhook %s in %.0f s", url, backoff)
        await asyncio.sleep(backoff)

    logger.error("Webhook %s gave up after %d attempts.", url, MAX_RETRIES)


async def dispatch_alert(alert: dict):
    """Fire alert to every registered webhook concurrently."""
    if not app_state.webhooks:
        logger.info("No webhooks registered — skipping dispatch.")
        return

    tasks = []
    for wh in app_state.webhooks:
        payload = get_payload(wh, alert)
        tasks.append(asyncio.create_task(send_with_retry(wh, payload)))

    await asyncio.gather(*tasks, return_exceptions=True)
