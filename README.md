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

