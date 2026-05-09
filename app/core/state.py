from dataclasses import dataclass, field
from typing import Optional
import asyncio


@dataclass
class AppState:
    # Monitoring config
    check_interval_seconds: int = 15
    request_timeout_ms: int = 3000

    # Live data
    proxies: dict = field(default_factory=dict)   # url -> ProxyRecord
    alerts: list = field(default_factory=list)    # list of AlertRecord dicts
    webhooks: list = field(default_factory=list)  # list of webhook dicts

    # Background task handle
    monitor_task: Optional[asyncio.Task] = None

    # Alert state — avoid sending duplicate alerts for same outage window
    alert_active: bool = False

    # Metrics trackers
    total_checks_counter: int = 0
    webhook_deliveries_counter: int = 0


app_state = AppState()
