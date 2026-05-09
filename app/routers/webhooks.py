from fastapi import APIRouter, status
import uuid
from app.core.state import app_state
from app.models.schemas import WebhookRequest

router = APIRouter(tags=["Webhooks"])


def normalize_platform(value: str | None) -> str:
    normalized = (value or "generic").strip().lower()
    if normalized in {"slack", "slack_block_kit", "slack-block-kit"}:
        return "slack"
    if normalized in {"discord", "discord_embeds", "discord-embeds"}:
        return "discord"
    return "generic"


def upsert_webhook(url: str, platform: str, secret: str | None, id_prefix: str = "wh") -> tuple[str, str]:
    webhook_id = f"{id_prefix}-{uuid.uuid4().hex[:6]}"
    normalized_platform = normalize_platform(platform)

    for webhook in app_state.webhooks:
        existing_url = webhook.get("url") if isinstance(webhook, dict) else webhook
        if existing_url == url:
            existing_id = webhook.get("id", webhook_id) if isinstance(webhook, dict) else webhook_id
            return existing_id, url

    app_state.webhooks.append({
        "id": webhook_id,
        "url": url,
        "platform": normalized_platform,
        "secret": secret,
    })
    return webhook_id, url


@router.post("/webhooks", status_code=status.HTTP_201_CREATED, summary="Register a webhook")
async def register_webhook(body: WebhookRequest):
    webhook_id, url = upsert_webhook(
        url=body.url,
        platform=body.platform,
        secret=body.secret,
        id_prefix="wh",
    )

    return {
        "webhook_id": webhook_id,
        "url": url
    }
