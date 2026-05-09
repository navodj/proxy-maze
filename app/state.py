from typing import Dict, List, Any
from app.models import Config

current_config = Config()
proxy_pool: Dict[str, dict] = {}
registered_webhooks: List[str] = []
alert_archive: List[Dict[str, Any]] = []
current_active_alert: Dict[str, Any] | None = None

# Metrics trackers
total_checks_counter: int = 0
webhook_deliveries_counter: int = 0