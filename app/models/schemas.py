from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---------- Config ----------
class ConfigRequest(BaseModel):
    check_interval_seconds: Optional[int] = None
    request_timeout_ms: Optional[int] = None
    # Backward compatibility keys
    check_interval: Optional[int] = None
    proxy_timeout: Optional[int] = None


class ConfigResponse(BaseModel):
    check_interval_seconds: int
    request_timeout_ms: int


# ---------- Proxies ----------
class ProxyItem(BaseModel):
    url: str


class ProxyListRequest(BaseModel):
    proxies: List[str]
    replace: Optional[bool] = False


class ProxyRecord(BaseModel):
    url: str
    status: str = "unknown"          # "up" | "down" | "unknown"
    last_checked: Optional[datetime] = None
    response_time_ms: Optional[float] = None
    failure_count: int = 0
    added_at: datetime = None

    def __init__(self, **data):
        if "added_at" not in data or data["added_at"] is None:
            data["added_at"] = datetime.utcnow()
        super().__init__(**data)


# ---------- Alerts ----------
class AlertRecord(BaseModel):
    id: str
    triggered_at: datetime
    total_proxies: int
    down_proxies: int
    failure_rate: float
    down_urls: List[str]
    resolved_at: Optional[datetime] = None


# ---------- Webhooks ----------
class WebhookRequest(BaseModel):
    url: str
    platform: Optional[str] = "generic"   # "slack" | "discord" | "generic"
    secret: Optional[str] = None


class WebhookRecord(BaseModel):
    id: str
    url: str
    platform: str = "generic"
    secret: Optional[str] = None
    created_at: datetime = None

    def __init__(self, **data):
        if "created_at" not in data or data["created_at"] is None:
            data["created_at"] = datetime.utcnow()
        super().__init__(**data)
