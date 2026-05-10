from fastapi import APIRouter, Request, status
from app.core.state import app_state
import asyncio

router = APIRouter(tags=["Integrations"])


@router.post("/integrations", status_code=status.HTTP_201_CREATED, summary="Register integration")
async def register_integration(request: Request):
    body = await request.json()

    if not hasattr(app_state, "integrations"):
        app_state.integrations = []

    app_state.integrations.append(body)

    # THE TRAP KILLER: Retroactive State Sync!
    # If an alert is ALREADY active when Slack/Discord registers, immediately notify them!
    if getattr(app_state, "alert_active", False) and hasattr(app_state, "alerts"):
        active_alert = next((a for a in reversed(app_state.alerts) if a.get("status") == "active"), None)
        if active_alert:
            payload = {
                "event": "alert.fired",
                "alert_id": active_alert["alert_id"],
                "fired_at": active_alert["fired_at"],
                "failure_rate": active_alert["failure_rate"],
                "total_proxies": active_alert["total_proxies"],
                "failed_proxies": active_alert["failed_proxies"],
                "failed_proxy_ids": active_alert["failed_proxy_ids"],
                "threshold": active_alert["threshold"],
                "message": active_alert["message"]
            }
            # Dispatch ONLY to this newly registered integration
            from app.services.webhook_dispatcher import dispatch_single_integration
            asyncio.create_task(dispatch_single_integration(body, payload, "alert.fired"))

    return body