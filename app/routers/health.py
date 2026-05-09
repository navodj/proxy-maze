from fastapi import APIRouter
from app.core.state import app_state

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Proof of Life")
async def health_check():
    return {"status": "ok"}


@router.get("/metrics", summary="The Control Room")
async def get_metrics():
    # Safely pull the active metrics from the application state
    total_checks = getattr(app_state, "total_checks_counter", 0)
    current_pool_size = len(app_state.proxies) if hasattr(app_state, "proxies") else 0
    active_alerts = 1 if getattr(app_state, "alert_active", False) else 0
    total_alerts = len(app_state.alerts) if hasattr(app_state, "alerts") else 0
    webhook_deliveries = getattr(app_state, "webhook_deliveries_counter", 0)

    return {
        "total_checks": total_checks,
        "current_pool_size": current_pool_size,
        "active_alerts": active_alerts,
        "total_alerts": total_alerts,
        "webhook_deliveries": webhook_deliveries
    }