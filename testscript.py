import requests
import time

# Your URLs (Base URL without /docs or /)
URLS = {
    "Render": "https://proxy-maze-od1n.onrender.com",
    "Tunnel": "https://alumni-lucid-pound.ngrok-free.dev"
}


def run_evaluation(name, base_url):
    print(f"\n--- Testing Environment: {name} ---")
    try:
        # 1. Chapter 01: Proof of Life
        r = requests.get(f"{base_url}/health", timeout=10)
        assert r.status_code == 200 and r.json().get("status") == "ok", "Health Check Failed"
        print(f"✅ [1] Health Check: OK")

        # 2. Chapter 02: The Heartbeat (Update Config)
        config = {"check_interval_seconds": 5, "request_timeout_ms": 2000}
        r = requests.post(f"{base_url}/config", json=config)
        assert r.status_code == 200, "Config Update Failed"
        print(f"✅ [2] Config Update: OK")

        # 3. Chapter 04: Building the Pool (Load 4 Proxies)
        # 1 failing proxy out of 4 = 25% (Fires the 0.20 threshold alert)
        proxy_payload = {
            "replace": True,
            "proxies": [
                "https://httpbin.org/status/200",
                "https://httpbin.org/status/200",
                "https://httpbin.org/status/200",
                "https://httpbin.org/status/500"  # Deliberate Failure
            ]
        }
        r = requests.post(f"{base_url}/proxies", json=proxy_payload)
        assert r.status_code == 201, "Proxy Ingestion Failed"
        print(f"✅ [4] Proxy Pool Loading: OK")

        # 4. Wait for Background Loop
        print(f"⏳ Waiting 12s for {name} background loop to cycle...")
        time.sleep(12)

        # 5. Chapter 05: The Watchtower (Verify Failure Rate)
        r = requests.get(f"{base_url}/proxies")
        data = r.json()
        f_rate = data.get("failure_rate", 0)
        assert f_rate >= 0.20, f"Failure Rate logic failed. Expected >= 0.20, got {f_rate}"
        print(f"✅ [5] Failure Rate Calculation: OK ({f_rate})")

        # 6. Chapter 09: Alert Archive (Verify Alert is Active)
        r = requests.get(f"{base_url}/alerts")
        alerts = r.json()
        assert len(alerts) > 0, "No alert recorded"
        assert any(a['status'] == 'active' for a in alerts), "No active alert found for the breach"
        print(f"✅ [9] Alert Lifecycle: OK (Active Alert Found)")

        return True
    except Exception as e:
        print(f"❌ TEST FAILED for {name}: {e}")
        return False


if __name__ == "__main__":
    results = {}
    for name, url in URLS.items():
        results[name] = run_evaluation(name, url)

    print("\n" + "=" * 30)
    print("FINAL VALIDATION SUMMARY:")
    for name, success in results.items():
        status = "PASSED 🏆" if success else "FAILED ❌"
        print(f"{name}: {status}")
    print("=" * 30)