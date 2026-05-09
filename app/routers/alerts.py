from fastapi import APIRouter
from app.core.state import app_state

router = APIRouter(tags=["Alerts"])

@router.get("/alerts", summary="View alert history")
async def list_alerts():
    """
    Chapter 09: The Alert Archive
    Returns all alerts, both active and resolved, as a raw JSON array.
    """
    # Simply return the list directly to satisfy the Black Box test.
    return app_state.alerts