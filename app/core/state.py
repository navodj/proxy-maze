from dataclasses import dataclass, field
from typing import Optional
import asyncio


@dataclass
class AppState:
    # Monitoring config
    check_interval: int = 15          # seconds between full sweeps
    proxy_timeout: int = 10           # seconds before a proxy check times out

    # Live data
    proxies: dict = field(default_factory=dict)   # url -> ProxyRecord
    alerts: list = field(default_factory=list)    # list of AlertRecord dicts
    webhooks: list = field(default_factory=list)  # list of webhook dicts

    # Background task handle
    monitor_task: Optional[asyncio.Task] = None

    # Alert state — avoid sending duplicate alerts for same outage window
    alert_active: bool = False


app_state = AppState()
