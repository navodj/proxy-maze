from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import List
from app.core.state import app_state

router = APIRouter(tags=["Integrations"])

class IntegrationRequest(BaseModel):
    type: str
    webhook_url: str
    username: str
    events: List[str]

    class Config:
        extra = "allow"

@router.post("/integrations", status_code=status.HTTP_201_CREATED, summary="Register integration")
async def register_integration(body: IntegrationRequest):
    if not hasattr(app_state, "integrations"):
        app_state.integrations = []

    integration_data = {
        "type": body.type,
        "webhook_url": body.webhook_url,
        "username": body.username,
        "events": body.events
    }

    app_state.integrations.append(integration_data)
    return integration_data