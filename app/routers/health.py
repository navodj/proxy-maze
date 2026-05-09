from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Server liveness check")
async def health():
    return {
        "status": "ok",
        "service": "Watchtower Proxy Monitor",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
