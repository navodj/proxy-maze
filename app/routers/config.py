from fastapi import APIRouter, HTTPException
from app.core.state import app_state
from app.models.schemas import ConfigRequest, ConfigResponse

router = APIRouter(tags=["Configuration"])


@router.post("/config", response_model=ConfigResponse, summary="Update monitoring config")
async def set_config(body: ConfigRequest):
    interval = body.check_interval_seconds
    if interval is None and body.check_interval is not None:
        interval = body.check_interval
    if interval is not None:
        if interval < 5:
            raise HTTPException(400, "check_interval_seconds must be >= 5")
        app_state.check_interval_seconds = interval

    timeout_ms = body.request_timeout_ms
    if timeout_ms is None and body.proxy_timeout is not None:
        timeout_ms = body.proxy_timeout * 1000
    if timeout_ms is not None:
        if timeout_ms < 1:
            raise HTTPException(400, "request_timeout_ms must be >= 1")
        app_state.request_timeout_ms = timeout_ms

    return ConfigResponse(
        check_interval_seconds=app_state.check_interval_seconds,
        request_timeout_ms=app_state.request_timeout_ms,
    )


@router.get("/config", response_model=ConfigResponse, summary="Get current config")
async def get_config():
    return ConfigResponse(
        check_interval_seconds=app_state.check_interval_seconds,
        request_timeout_ms=app_state.request_timeout_ms,
    )
