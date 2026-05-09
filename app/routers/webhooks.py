import uuid
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone

from app.core.state import app_state
from app.models.schemas import WebhookRequest

router = APIRouter(tags=["Webhooks"])


@router.post("/webhooks", summary="Register a webhook URL to receive alerts")
async def add_webhook(body: WebhookRequest):
    # Prevent duplicates for the same URL
    for wh in app_state.webhooks:
        if wh["url"] == body.url:
            return {"message": "Webhook URL already registered.", "webhook": wh}

    record = {
        "id": str(uuid.uuid4()),
        "url": body.url,
        "platform": body.platform or "generic",
        "secret": body.secret,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    app_state.webhooks.append(record)
    return {"message": "Webhook registered.", "webhook": record}


@router.get("/webhooks", summary="List registered webhooks")
async def list_webhooks():
    # Mask secrets in response
    safe = []
    for wh in app_state.webhooks:
        entry = dict(wh)
        if entry.get("secret"):
            entry["secret"] = "***"
        safe.append(entry)
    return {"total": len(safe), "webhooks": safe}


@router.delete("/webhooks/{webhook_id}", summary="Remove a webhook by ID")
async def delete_webhook(webhook_id: str):
    for i, wh in enumerate(app_state.webhooks):
        if wh["id"] == webhook_id:
            app_state.webhooks.pop(i)
            return {"message": f"Webhook {webhook_id} removed."}
    raise HTTPException(404, f"Webhook '{webhook_id}' not found.")


@router.delete("/webhooks", summary="Remove all webhooks")
async def clear_webhooks():
    count = len(app_state.webhooks)
    app_state.webhooks.clear()
    return {"message": f"Cleared {count} webhooks."}


@router.post("/webhooks/test", summary="Send a test alert to all registered webhooks")
async def test_webhooks():
    from app.services.webhook_dispatcher import dispatch_alert
    import asyncio

    if not app_state.webhooks:
        raise HTTPException(400, "No webhooks registered.")

    test_alert = {
        "id": "test-" + str(uuid.uuid4())[:8],
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "total_proxies": 10,
        "down_proxies": 3,
        "failure_rate": 0.30,
        "down_urls": ["https://example.com/proxy1", "https://example.com/proxy2"],
        "resolved_at": None,
    }
    asyncio.create_task(dispatch_alert(test_alert))
    return {"message": "Test alert dispatched.", "alert": test_alert}
