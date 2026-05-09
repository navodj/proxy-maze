import time
import httpx

BASE_URL = "https://proxy-maze-od1n.onrender.com"
WEBHOOK_URL = "https://webhook.site/a17dfa4b-0e2e-47f3-8091-833e4d5b92a8"  # 🔁 replace this

def register_webhook():
    print("📡 Registering webhook...")
    res = httpx.post(
        f"{BASE_URL}/webhooks",
        json={"url": WEBHOOK_URL},
        timeout=10
    )
    print("Status:", res.status_code)
    print(res.text)


def trigger_failure():
    print("\n🔥 Sending failing proxies...")
    res = httpx.post(
        f"{BASE_URL}/proxies",
        json={
            "replace": True,
            "proxies": [
                "https://httpbin.org/status/200",
                "https://httpbin.org/status/200",
                "https://httpbin.org/status/200",
                "https://httpbin.org/status/500"
            ]
        },
        timeout=10
    )
    print("Status:", res.status_code)


def resolve_alert():
    print("\n✅ Sending healthy proxies...")
    res = httpx.post(
        f"{BASE_URL}/proxies",
        json={
            "replace": True,
            "proxies": [
                "https://httpbin.org/status/200",
                "https://httpbin.org/status/200"
            ]
        },
        timeout=10
    )
    print("Status:", res.status_code)


def main():
    print("🚀 Starting test sequence...")

    register_webhook()
    time.sleep(2)

    trigger_failure()
    print("⏳ Waiting for alert to trigger...")
    time.sleep(20)

    resolve_alert()
    print("⏳ Waiting for alert resolution...")
    time.sleep(20)

    print("\n✅ Test completed. Check webhook.site!")


if __name__ == "__main__":
    main()