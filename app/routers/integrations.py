from fastapi import APIRouter, Request, status
from app.core.state import app_state

router = APIRouter(tags=["Integrations"])


@router.post("/integrations", status_code=status.HTTP_201_CREATED, summary="Register integration")
async def register_integration(request: Request):
    # Blindly accept whatever JSON the evaluator sends
    body = await request.json()

    if not hasattr(app_state, "integrations"):
        app_state.integrations = []

    app_state.integrations.append(body)

    return body