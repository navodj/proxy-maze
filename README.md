# 🗼 Watchtower — Proxy Monitor

Real-time proxy health monitoring API with automatic webhook alerting.
Built with **FastAPI** + **httpx** async.

---

## Features

| Feature | Detail |
|---|---|
| Background monitor | Runs every N seconds (default 15), fully async |
| Failure rate rule | Alert fires when ≥ 20% of proxies are DOWN |
| Webhook delivery | Retries up to 10× with exponential back-off |
| Slack support | Block Kit formatted messages (bonus) |
| Discord support | Embed formatted messages (bonus) |
| Immediate check | New proxies checked instantly on upload |

---

## Quick Start (local)

```bash
# 1. Clone / unzip the project
cd watchtower

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 4. Open interactive docs
open http://localhost:8000/docs
```

---

## Deployment

### Render.com (recommended — free tier)
1. Push the project to a GitHub repo.
2. Create a new **Web Service** on Render, connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Deploy — Render gives you a public HTTPS URL.

### Railway
```bash
railway init
railway up
```

### Docker
```bash
docker build -t watchtower .
docker run -p 8000:8000 watchtower
```

### Local tunnel (ngrok)
```bash
uvicorn main:app --port 8000 &
ngrok http 8000
```

---

## API Endpoints

### Chapter 1 — Health
```
GET /health
```
Returns `{"status":"ok"}`. Use this to confirm the server is alive.

---

### Chapter 2 — Config
```
POST /config
GET  /config
```
**Body:**
```json
{
  "check_interval_seconds": 15,
  "request_timeout_ms": 3000
}
```
- `check_interval_seconds` — seconds between automatic check sweeps (min 5)
- `request_timeout_ms` — timeout for each proxy check in milliseconds (min 1)

---

### Chapter 3 — Add Proxies
```
POST /proxies
```
**Body:**
```json
{
  "proxies": [
    "https://proxy1.example.com",
    "https://proxy2.example.com"
  ]
}
```
Triggers an **immediate check cycle** right after adding. Duplicates are ignored.

---

### Chapter 4 — List Proxies
```
GET /proxies
```
Returns every proxy URL with its current `up` / `down` / `unknown` status, last-checked timestamp, and response time.

---

### Chapter 5 — Delete Proxies
```
DELETE /proxies              # clear all
DELETE /proxies/{url}        # remove one
```

---

### Chapter 6 — Trigger Manual Check
```
POST /proxies/check
```
Fires an immediate background check cycle without waiting for the next scheduled sweep.

---

### Chapter 7 — Alerts
```
GET  /alerts
GET  /alerts?unresolved_only=true
DELETE /alerts
```
Returns the full history of alert events, newest first.

---

### Chapter 8 — Register Webhook
```
POST /webhooks
```
**Body:**
```json
{
  "url": "https://your-receiver.example.com/hook",
  "platform": "generic",
  "secret": "optional-shared-secret"
}
```
`platform` options: `generic` (default), `slack`, `discord`

---

### Chapter 9 — List Webhooks
```
GET /webhooks
```

---

### Chapter 10 — Delete Webhook
```
DELETE /webhooks/{webhook_id}
DELETE /webhooks
```

---

### Chapter 11 — Test Webhook
```
POST /webhooks/test
```
Sends a synthetic test alert to all registered webhooks immediately.

---

### Chapter 12 — Docs
```
GET /docs    ← Swagger UI
GET /redoc   ← ReDoc
```

---

## Alert Payload (generic)

When failure rate ≥ 20%, Watchtower POSTs this JSON to every registered webhook:

```json
{
  "event": "proxy_alert",
  "alert_id": "uuid",
  "triggered_at": "2024-01-01T12:00:00+00:00",
  "total_proxies": 10,
  "down_proxies": 3,
  "failure_rate_pct": 30.0,
  "down_urls": ["https://proxy1.example.com"],
  "message": "🚨 Watchtower Alert — 3/10 proxies are DOWN (30.0% failure rate)."
}
```

If the webhook URL is down, Watchtower **retries up to 10 times** using exponential back-off (2s, 4s, 8s … capped at 120s).

---

## Slack Payload (bonus)

Register with `"platform": "slack"` to receive Block Kit formatted messages with structured fields.

## Discord Payload (bonus)

Register with `"platform": "discord"` to receive rich embeds with red color and all alert details.

---

## Scoring checklist

- [x] `GET /health`
- [x] `POST /config` + `GET /config`
- [x] `POST /proxies` (with immediate background check)
- [x] `GET /proxies` (status + failure rate)
- [x] `DELETE /proxies`
- [x] `POST /proxies/check`
- [x] `GET /alerts`
- [x] `POST /webhooks`
- [x] `GET /webhooks`
- [x] `DELETE /webhooks/{id}`
- [x] `POST /webhooks/test`
- [x] Background monitoring loop (asyncio)
- [x] Failure rate ≥ 20% triggers alert
- [x] Webhook retry with exponential back-off
- [x] Slack Block Kit formatting (bonus)
- [x] Discord embed formatting (bonus)
