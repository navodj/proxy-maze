from fastapi import APIRouter, status
import uuid
from app.core.state import app_state
from app.models.schemas import WebhookRequest

router = APIRouter(tags=["Webhooks"])

@router.post("/webhooks", status_code=status.HTTP_201_CREATED, summary="Register a webhook")
async def register_webhook(body: WebhookRequest):
    webhook_id = f"wh-{uuid.uuid4().hex[:6]}"

    if not hasattr(app_state, "webhooks"):
        app_state.webhooks = []

    # Store the platform!
    webhook_data = {
        "id": webhook_id,
        "url": body.url,
        "platform": body.platform or "generic"
    }

    # Avoid duplicate URLs
    if not any(isinstance(w, dict) and w["url"] == body.url for w in app_state.webhooks):
        app_state.webhooks.append(webhook_data)

    return {
        "webhook_id": webhook_id,
        "url": body.url
    }