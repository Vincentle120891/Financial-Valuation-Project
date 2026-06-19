# Launching Plan — FinGrid (Financial Valuation Platform)

> Status: Deployment-Ready | Target: EPYCHN-2 Hanoi VPS
> Stack: Docker Compose + Caddy (auto-SSL) + VPS persistent storage

---

## 1. Architecture Overview

EPYCHN-2 VPS hosts all three services via Docker Compose. Caddy provides automatic SSL and reverse proxy routing.

```
┌─────────────────────────────────────────────────────────────────┐
│                        EPYCHN-2 Hanoi VPS                       │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Caddy       │  │   Frontend   │  │   Backend            │  │
│  │   :80/:443    │──│   Nginx      │──│   FastAPI+Uvicorn    │  │
│  │   Auto-SSL    │  │   :3000      │  │   :8000              │  │
│  │   Routing     │  │   Static     │  │   2 workers          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│         │                                    │                   │
│         └──────────── /api/* ───────────────┘                   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   Persistent Storage (Docker Volume)                     │   │
│  │   /app/data → session data, future DB                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

| Component | Service | Why |
|---|---|---|
| Backend | FastAPI + Uvicorn (2 workers) | Async financial calculations |
| Frontend | React + Nginx | Static SPA with gzip |
| Reverse Proxy | Caddy 2 | Auto-SSL, zero-config HTTPS |
| Storage | Docker Volume (NVMe RAID-10) | Persistent sessions |

---

## 2. Why VPS Over Cloud Run

| Factor | Cloud Run (old plan) | VPS (EPYCHN-2) |
|---|---|---|
| Cold starts | 1-3s latency | Zero — always running |
| Persistent state | In-memory only (lost on restart) | Docker volume on NVMe |
| Cost | $0-1/month (free tier) | Fixed server cost |
| Latency (Vietnam) | US-East ~200ms | Hanoi ~5ms |
| PDF processing | Timeouts on cold starts | Unlimited compute |
| WebSocket | Not supported | Full support |
| Control | Limited | Full root access |

---

## 3. Deployment Files

All deployment files are in [`deploy/`](../deploy/):

```
deploy/
├── backend/
│   └── Dockerfile              # Multi-stage Python 3.12 + system deps
├── frontend/
│   ├── Dockerfile              # Multi-stage Node 20 → Nginx
│   └── nginx.conf              # SPA routing + gzip + caching
├── docker-compose.yml          # 3-service orchestration
├── Caddyfile                   # Reverse proxy + SSL + security headers
├── .env.example                # Environment variable template
└── deploy.sh                   # One-command deployment script
```

---

## 4. Backend Dockerfile Key Fixes

| Issue | Old Script | Fixed |
|---|---|---|
| Entry point | `uvicorn main:app` | `uvicorn app.main:app` |
| System deps | None | ghostscript, java, poppler, tesseract |
| Health check | None | `curl -f http://localhost:8000/health` |
| Copy context | `COPY . .` (wrong path) | `COPY app/ ./app/` |

See [`deploy/backend/Dockerfile`](../deploy/backend/Dockerfile)

---

## 5. Frontend Dockerfile Key Fixes

| Issue | Old Script | Fixed |
|---|---|---|
| `VITE_API_URL` | Not passed | Build arg injected at compile time |
| Nginx config | Inline heredoc (broken) | Separate `nginx.conf` file |
| SPA routing | None | `try_files $uri $uri/ /index.html` |
| Caching | None | 1-year cache for static assets |

See [`deploy/frontend/Dockerfile`](../deploy/frontend/Dockerfile)

---

## 6. Docker Compose Configuration

See [`deploy/docker-compose.yml`](../deploy/docker-compose.yml)

### Key Features
- **Health checks**: Backend (`/health`) and frontend (`wget`) with `service_healthy` condition
- **Dependency ordering**: Caddy waits for both services to be healthy before starting
- **Persistent volume**: `backend_data` mounted at `/app/data`
- **Network isolation**: Internal `fingrid` bridge network
- **Environment injection**: `.env` file mounted read-only

---

## 7. Caddy Reverse Proxy

See [`deploy/Caddyfile`](../deploy/Caddyfile)

### Routing Rules
| Path | Destination | Purpose |
|---|---|---|
| `/api/*` | `backend:8000` | FastAPI valuation endpoints |
| `/docs*`, `/redoc*`, `/openapi.json` | `backend:8000` | API documentation |
| `/health*` | `backend:8000` | Health checks |
| `*` (everything else) | `frontend:3000` | React SPA |

### Security Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Server` header removed

---

## 8. Environment Variables

See [`deploy/.env.example`](../deploy/.env.example)

### Required
| Variable | Value | Notes |
|---|---|---|
| `ENVIRONMENT` | `production` | Disables debug mode |
| `VITE_API_URL` | `https://yourdomain.com/api` | Baked into frontend at build time |
| `CORS_ORIGINS` | `["https://yourdomain.com"]` | Backend CORS whitelist |

### Optional (API Keys as server fallbacks)
| Variable | Purpose |
|---|---|
| `ALPHA_VANTAGE_API_KEY` | Financial data API |
| `FMP_API_KEY` | Financial Modeling Prep |
| `FRED_API_KEY` | US Treasury yields |
| `OPENROUTER_API_KEY` | Primary AI provider |
| `GROQ_API_KEY` | Alternative AI provider |

> **Note**: Users bring their own API keys via the Step 1 modal. Server-side keys are fallbacks only.

---

## 9. Database Persistence

### Current Status: In-Memory Sessions
- Sessions stored in Python `dict` — data lost on container restart
- **Acceptable for V1**: Users run valuations in a single session

### V2: MongoDB Persistence
See [`plans/database-persistence-plan.md`](database-persistence-plan.md)

| Phase | What | When |
|---|---|---|
| V1 | In-memory sessions | Now |
| V2 | MongoDB via `motor` | After first users |
| V3 | User accounts + saved reports | After V2 |

### Migration Path
When ready for MongoDB:
1. Add `mongo` service to `docker-compose.yml`
2. Add `motor` + `pymongo` to `requirements.txt`
3. Implement [`plans/database-persistence-plan.md`](database-persistence-plan.md) Step 1-7

---

## 10. Step-by-Step Deployment Guide

### Prerequisites
Before starting, you need:
- [ ] SSH access to EPYCHN-2 (`ssh vincent@<VPS_IP>`)
- [ ] A domain name pointed to the VPS IP (e.g., `platform.yourdomain.com`)
- [ ] Git installed on VPS (`git --version`)
- [ ] Docker installed on VPS (we'll install in Step 1)

---

### Step 1: Prepare the VPS (First Time Only)

SSH into the VPS and install Docker:

```bash
# Connect to VPS
ssh vincent@<VPS_IP>

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose-plugin

# Allow your user to run Docker without sudo
sudo usermod -aG docker vincent

# IMPORTANT: Log out and back in for group change to take effect
exit
```

After logging back in, verify Docker works:
```bash
docker --version
# Expected: Docker version 24.x.x or newer

docker compose version
# Expected: Docker Compose version v2.x.x
```

**✅ Checkpoint**: Docker is installed and your user can run it without `sudo`.

---

### Step 2: Clone the Repository

```bash
cd /home/vincent

# Clone the project (replace with your actual repo URL)
git clone <YOUR_REPO_URL> Financial-Valuation-Project

# Verify the structure
ls Financial-Valuation-Project/deploy/
# Expected: Caddyfile  .env.example  deploy.sh  docker-compose.yml  backend/  frontend/
```

**✅ Checkpoint**: Repository cloned with all deployment files present.

---

### Step 3: Configure Environment Variables

```bash
cd /home/vincent/Financial-Valuation-Project/deploy

# Copy the template
cp .env.example .env

# Edit with your settings
nano .env
```

**Critical values to set in `.env`:**

```bash
# Your domain (required for SSL + CORS)
VITE_API_URL=https://platform.yourdomain.com/api
CORS_ORIGINS=["https://platform.yourdomain.com"]

# Production mode
ENVIRONMENT=production
DEBUG=false
```

Save and exit (`Ctrl+X`, `Y`, `Enter`).

Also update the Caddyfile AND .env with your actual domain (both files must match):
```bash
# Replace platform.yourdomain.com with your real domain in BOTH files simultaneously
sed -i 's/platform.yourdomain.com/YOUR_ACTUAL_DOMAIN/g' Caddyfile .env
```

**⚠️ Critical**: Both `Caddyfile` AND `.env` must have the same domain. If they differ, the frontend will bake the wrong URL at build time and API calls will fail with CORS errors.

**✅ Checkpoint**: `.env` AND `Caddyfile` both configured with your domain.

---

### Step 4: Run the Deployment Script

```bash
# Make the script executable
chmod +x deploy.sh

# Run it (this builds Docker images — takes 5-10 minutes on first run)
./deploy.sh
```

The script will:
1. Create deployment directories
2. Copy source code to deployment location
3. Build backend Docker image (Python 3.12 + system deps)
4. Build frontend Docker image (Node 20 build → Nginx)
5. Start all 3 containers (backend, frontend, caddy)
6. Verify health checks

**✅ Checkpoint**: All 3 containers are running. Watch for "Deployment complete!" message.

---

### Step 5: Verify Deployment

```bash
# Check container status
docker compose ps
# Expected: 3 containers (backend, frontend, caddy) all "Up" and "healthy"

# Check backend health
curl http://localhost:8000/health
# Expected: {"status": "healthy", "version": "2.0.0", ...}

# Check backend readiness
curl http://localhost:8000/health/ready
# Expected: {"status": "ready", ...}

# Check frontend
curl -s http://localhost:3000/ | head -5
# Expected: HTML content (React app)

# Check Caddy (through port 80)
curl -s http://localhost:80/health
# Expected: {"status": "healthy", ...}
```

**✅ Checkpoint**: All services respond correctly on localhost.

---

### Step 6: Configure DNS

1. Go to your domain registrar (Namecheap, Cloudflare, GoDaddy, etc.)
2. Add an **A Record**:
   - **Name**: `platform` (or your subdomain)
   - **Value**: `<VPS_PUBLIC_IP>`
   - **TTL**: 300 (5 minutes)
3. Wait for DNS propagation (usually 5-15 minutes, can take up to 24 hours)

Verify DNS is working:
```bash
# From your local machine
nslookup platform.yourdomain.com
# Expected: Address: <VPS_PUBLIC_IP>

# Or use dig
dig platform.yourdomain.com +short
# Expected: <VPS_PUBLIC_IP>
```

**✅ Checkpoint**: DNS resolves your domain to the VPS IP.

---

### Step 7: Test SSL & HTTPS

Once DNS propagates, Caddy will automatically provision an SSL certificate from Let's Encrypt.

```bash
# Test HTTPS from your local machine
curl -I https://platform.yourdomain.com/
# Expected: HTTP/2 200, with SSL certificate

# Test the health endpoint via HTTPS
curl https://platform.yourdomain.com/health
# Expected: {"status": "healthy", ...}

# Test API endpoint
curl -X POST https://platform.yourdomain.com/api/step-1-search \
  -H "Content-Type: application/json" \
  -d '{"query": "AAPL", "market": "international"}'
# Expected: JSON with search results
```

If SSL fails, check Caddy logs:
```bash
docker compose logs caddy | tail -20
```

**✅ Checkpoint**: HTTPS works, API responds, SSL certificate is valid.

---

### Step 8: End-to-End Test (Browser)

1. Open `https://platform.yourdomain.com` in your browser
2. You should see the FinGrid interface
3. Walk through the full workflow:
   - **Step 1**: Search for "AAPL"
   - **Step 2**: Select Apple Inc. → creates session
   - **Step 3**: Select DCF model
   - **Step 4**: Discover peers
   - **Step 5**: View required inputs
   - **Step 6**: Fetch API data
   - **Step 7**: Retrieve historical data
   - **Step 8**: Configure forecast drivers
   - **Step 9**: Confirm assumptions
   - **Step 10**: Run valuation → see results

**✅ Checkpoint**: Full 10-step workflow works in production.

---

### Step 9: Set Up Automatic Updates (Optional)

Create a zero-downtime deploy script on the VPS:

```bash
cat > /home/vincent/update-fingrid.sh << 'EOF'
#!/bin/bash
set -e
cd /home/vincent/Financial-Valuation-Project
git pull

cd deploy

# 1. Build fresh images in background (old containers keep serving traffic)
#    Uses Docker layer caching — only rebuilds changed layers (fast!)
docker compose build backend frontend

# 2. Instantly recreate containers with near-zero downtime
docker compose up -d --no-deps backend frontend

# 3. Clean up old dangling images to preserve NVMe space
docker system prune -f

echo "✅ FinGrid updated with near-zero downtime at $(date)"
EOF

chmod +x /home/vincent/update-fingrid.sh
```

**⚠️ Why not `docker compose down`?** That destroys containers and network routing, causing 5-10 minutes of downtime while `--no-cache` rebuilds everything from scratch. The approach above builds while old containers serve traffic, then swaps in under 2 seconds.

Now to deploy updates:
```bash
ssh vincent@<VPS_IP>
/home/vincent/update-fingrid.sh
```

---

### Step 10: Log Rotation (Already Configured)

Log rotation is **already handled** by the Docker logging driver in [`docker-compose.yml`](../deploy/docker-compose.yml):

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"   # Rotates when a log file hits 10MB
    max-file: "3"     # Retains max 3 historical rotations
```

This applies to all 3 services (backend, frontend, caddy). Each service keeps at most 30MB of logs (3 × 10MB). No cron job needed.

To check current log sizes:
```bash
docker system df -v | grep "Local Volumes"
```

To manually prune all unused Docker data:
```bash
docker system prune -a -f  # Removes all unused images, containers, networks
```

---

## 11. Quick Reference Commands

```bash
# === DEPLOYMENT ===
cd /home/vincent/Financial-Valuation-Project/deploy

# First deploy
./deploy.sh

# Update after git pull (zero-downtime)
docker compose build backend frontend && docker compose up -d --no-deps backend frontend && docker system prune -f

# === MONITORING ===
docker compose ps                    # Container status
docker compose logs -f               # All logs (live)
docker compose logs -f backend       # Backend only
docker compose logs --tail 50 caddy  # Last 50 Caddy lines
docker stats                         # CPU/memory usage

# === MAINTENANCE ===
docker compose restart backend       # Restart backend only
docker compose down                  # Stop everything
docker compose up -d                 # Start everything
docker system prune -f               # Clean unused Docker images

# === TROUBLESHOOTING ===
docker compose logs backend | tail -30   # Backend errors
curl http://localhost:8000/health         # Backend health
curl http://localhost:3000/               # Frontend health
```

---

## 12. Troubleshooting

| Problem | Solution |
|---|---|
| Backend won't start | Check `docker compose logs backend` — usually missing env vars |
| Frontend shows blank page | Check `VITE_API_URL` in `.env` matches your domain |
| SSL certificate fails | Verify DNS is pointing to VPS IP, wait 15 min for Let's Encrypt |
| "Connection refused" from API | Check `docker compose ps` — backend container may be restarting |
| Build fails on `pip install` | Check `requirements.txt` — may need system deps in Dockerfile |
| Port 80/443 already in use | Stop other web servers: `sudo systemctl stop apache2 nginx` |
| Container exits immediately | Run `docker compose logs <service>` to see the error |

---

## 13. Cost Analysis

| Item | Monthly Cost |
|---|---|
| EPYCHN-2 VPS | Fixed server cost |
| Domain (optional) | ~$0.83/month ($10/year) |
| Docker images | $0 (self-hosted) |
| SSL certificates | $0 (Let's Encrypt via Caddy) |
| **Total** | **VPS cost only** |

---

## 14. Future Enhancements

| Phase | Feature | Priority |
|---|---|---|
| V1.1 | MongoDB session persistence | P1 |
| V1.2 | User authentication (Supabase or custom) | P1 |
| V2 | Vietnam market integration | P2 |
| V2.1 | Saved valuations + history | P2 |
| V2.2 | PDF report generation | P2 |
| V3 | Multi-user collaboration | P3 |
| V3.1 | WebSocket real-time updates | P3 |
