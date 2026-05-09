import httpx
import asyncio
import logging
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
                    # Track successful deliveries for the metrics endpoint
                    if not hasattr(app_state, "webhook_deliveries_counter"):
                        app_state.webhook_deliveries_counter = 0
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

        if attempt < max_retries:
            await asyncio.sleep(base_delay * attempt)


async def dispatch_alert(payload: dict):
    if not app_state.webhooks:
        return

    # Dispatch to all registered capture URLs concurrently
    tasks = [send_with_retry(url, payload) for url in app_state.webhooks]
    await asyncio.gather(*tasks)
