from pydantic import BaseModel
from typing import List, Optional


class Config(BaseModel):
    check_interval_seconds: int = 15
    request_timeout_ms: int = 3000


class ProxyPayload(BaseModel):
    proxies: List[str]
    replace: Optional[bool] = False


class WebhookPayload(BaseModel):
    url: str

    class Config:
        extra = "allow"