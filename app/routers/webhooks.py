from fastapi import APIRouter, status
import uuid
from app.core.state import app_state
from app.models.schemas import WebhookRequest

router = APIRouter(tags=["Webhooks"])


@router.post("/webhooks", status_code=status.HTTP_201_CREATED, summary="Register a webhook")
async def register_webhook(body: WebhookRequest):
    webhook_id = f"wh-{uuid.uuid4().hex[:6]}"

    # Initialize the list if it doesn't exist in state yet
    if not hasattr(app_state, "webhooks"):
        app_state.webhooks = []

    if body.url not in app_state.webhooks:
        app_state.webhooks.append(body.url)

    return {
        "webhook_id": webhook_id,
        "url": body.url
    }