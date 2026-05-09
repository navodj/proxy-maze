from fastapi import APIRouter, Query
from app.core.state import app_state

router = APIRouter(tags=["Alerts"])


@router.get("/alerts", summary="View alert history")
async def list_alerts(
    limit: int = Query(50, ge=1, le=500, description="Max number of alerts to return"),
    unresolved_only: bool = Query(False, description="Only return open (unresolved) alerts"),
):
    alerts = app_state.alerts
    if unresolved_only:
        alerts = [a for a in alerts if a.get("resolved_at") is None]
    alerts = alerts[-limit:][::-1]   # newest first

    return {
        "total": len(app_state.alerts),
        "returned": len(alerts),
        "alert_active": app_state.alert_active,
        "alerts": alerts,
    }


@router.delete("/alerts", summary="Clear alert history")
async def clear_alerts():
    count = len(app_state.alerts)
    app_state.alerts.clear()
    app_state.alert_active = False
    return {"message": f"Cleared {count} alerts."}
