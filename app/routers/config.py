from fastapi import APIRouter, HTTPException
from app.core.state import app_state
from app.models.schemas import ConfigRequest, ConfigResponse

router = APIRouter(tags=["Configuration"])


@router.post("/config", response_model=ConfigResponse, summary="Update monitoring config")
async def set_config(body: ConfigRequest):
    if body.check_interval is not None:
        if body.check_interval < 5:
            raise HTTPException(400, "check_interval must be ≥ 5 seconds")
        app_state.check_interval = body.check_interval

    if body.proxy_timeout is not None:
        if body.proxy_timeout < 1:
            raise HTTPException(400, "proxy_timeout must be ≥ 1 second")
        app_state.proxy_timeout = body.proxy_timeout

    return ConfigResponse(
        check_interval=app_state.check_interval,
        proxy_timeout=app_state.proxy_timeout,
    )


@router.get("/config", response_model=ConfigResponse, summary="Get current config")
async def get_config():
    return ConfigResponse(
        check_interval=app_state.check_interval,
        proxy_timeout=app_state.proxy_timeout,
    )
