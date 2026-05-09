import httpx
import asyncio
from app import state


async def send_webhook_with_retry(url: str, payload: dict):
    max_retries = 5
    base_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=5.0)

                if 200 <= response.status_code < 300:
                    state.webhook_deliveries_counter += 1
                    print(f"✅ Webhook delivered successfully to {url}")
                    return

                if response.status_code in [500, 502, 503, 504]:
                    print(f"⚠️ Transient error {response.status_code} from {url}. Retrying...")
                else:
                    print(f"❌ Failed to deliver to {url}: Status {response.status_code}")
                    return

        except (httpx.RequestError, httpx.TimeoutException) as e:
            print(f"⚠️ Connection error to {url}: {e}. Retrying...")

        await asyncio.sleep(base_delay * (attempt + 1))


async def dispatch_all_webhooks(event_type: str, alert_data: dict):
    if not state.registered_webhooks:
        return

    payload = {"event": event_type}

    if event_type == "alert.fired":
        payload.update({
            "alert_id": alert_data["alert_id"],
            "fired_at": alert_data["fired_at"],
            "failure_rate": alert_data["failure_rate"],
            "total_proxies": alert_data["total_proxies"],
            "failed_proxies": alert_data["failed_proxies"],
            "failed_proxy_ids": alert_data["failed_proxy_ids"],
            "threshold": alert_data["threshold"],
            "message": alert_data["message"]
        })
    elif event_type == "alert.resolved":
        payload.update({
            "alert_id": alert_data["alert_id"],
            "resolved_at": alert_data["resolved_at"]
        })

    tasks = [send_webhook_with_retry(url, payload) for url in state.registered_webhooks]
    await asyncio.gather(*tasks)