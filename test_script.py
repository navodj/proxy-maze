import time
import httpx

BASE_URL = "https://unengaged-proximity-grime.ngrok-free.dev"  # You can also use your ngrok URL here
WEBHOOK_URL = "https://webhook.site/46789a97-be36-4bfe-8141-f53f8e90fda0"  # ⚠️ REPLACE THIS!


def test_health():
    print("1. Testing /health...")
    r = httpx.get(f"{BASE_URL}/health")
    print(f"   Status: {r.status_code}, Response: {r.json()}")


def register_webhooks():
    print("\n2. Registering Webhooks (Generic, Slack, Discord)...")
    # We add URL parameters (?type=...) just so you can easily tell them apart on webhook.site
    httpx.post(f"{BASE_URL}/webhooks", json={"url": f"{WEBHOOK_URL}?type=generic", "platform": "generic"})
    httpx.post(f"{BASE_URL}/webhooks", json={"url": f"{WEBHOOK_URL}?type=slack", "platform": "slack"})
    r = httpx.post(f"{BASE_URL}/webhooks", json={"url": f"{WEBHOOK_URL}?type=discord", "platform": "discord"})
    print(f"   Status: {r.status_code}")


def set_config():
    print("\n3. Setting Config (5s interval)...")
    r = httpx.post(f"{BASE_URL}/config", json={"check_interval_seconds": 5, "request_timeout_ms": 2000})
    print(f"   Status: {r.status_code}")


def trigger_breach():
    print("\n4. Triggering Breach (25% failure rate)...")
    r = httpx.post(f"{BASE_URL}/proxies", json={
        "replace": True,
        "proxies": [
            "https://httpbin.org/status/200",
            "https://httpbin.org/status/200",
            "https://httpbin.org/status/200",
            "https://httpbin.org/status/500"  # This 500 error triggers the breach
        ]
    })
    print(f"   Status: {r.status_code}, Accepted: {r.json().get('accepted')}")


def check_alerts():
    print("\n5. Checking Alerts Archive...")
    r = httpx.get(f"{BASE_URL}/alerts")
    alerts = r.json()
    print(f"   Total Alerts: {len(alerts)}")
    if len(alerts) > 0:
        print(f"   Latest Alert Status: {alerts[-1].get('status')}")


def resolve_breach():
    print("\n6. Resolving Breach (100% healthy)...")
    r = httpx.post(f"{BASE_URL}/proxies", json={
        "replace": True,
        "proxies": [
            "https://httpbin.org/status/200",
            "https://httpbin.org/status/200"
        ]
    })
    print(f"   Status: {r.status_code}")


def main():
    print("🚀 Starting Watchtower Evaluator Simulation...\n")
    test_health()
    register_webhooks()
    set_config()
    trigger_breach()

    print("⏳ Waiting 8 seconds for background loop to detect breach and fire webhooks...")
    time.sleep(8)
    check_alerts()

    resolve_breach()
    print("⏳ Waiting 8 seconds for background loop to resolve and fire webhooks...")
    time.sleep(8)
    check_alerts()

    print("\n✅ Simulation Complete! Check your webhook.site dashboard to verify the payloads.")


if __name__ == "__main__":
    main()