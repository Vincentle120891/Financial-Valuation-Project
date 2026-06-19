# FinGrid VPS Deployment Guide

> Complete instructions for deploying the Financial Valuation Platform to a VPS.
> Last updated: 2026-06-19

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Server Preparation](#3-server-preparation)
4. [Clone & Configure](#4-clone--configure)
5. [Environment Variables](#5-environment-variables)
6. [Build & Deploy](#6-build--deploy)
7. [DNS & SSL](#7-dns--ssl)
8. [Verification](#8-verification)
9. [Updates & Maintenance](#9-updates--maintenance)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Your VPS                              │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Caddy       │  │   Frontend   │  │   Backend        │  │
│  │   :80/:443    │──│   Nginx      │──│   FastAPI        │  │
│  │   Auto-SSL    │  │   :3000      │  │   Uvicorn 2w     │  │
│  │   Routing     │  │   Static SPA │  │   :8000          │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│         │                                    │               │
│         └──────────── /api/* ───────────────┘               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │   Docker Volumes (persistent storage)                 │   │
│  │   backend_data → /app/data (sessions, peer cache)     │   │
│  │   caddy_data   → SSL certificates                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

| Component | Technology | Port | Purpose |
|-----------|-----------|------|---------|
| Backend | FastAPI + Uvicorn (2 workers) | 8000 | Financial calculations, API |
| Frontend | React + Vite → Nginx | 3000 | Static SPA |
| Reverse Proxy | Caddy 2 | 80/443 | Auto-SSL, HTTPS, routing |

---

## 2. Prerequisites

- [ ] VPS with Ubuntu 22.04+ (recommended: 2+ GB RAM, 20+ GB disk)
- [ ] SSH access to the VPS
- [ ] A domain name (e.g., `platform.yourdomain.com`)
- [ ] DNS A record pointing your domain to the VPS public IP

---

## 3. Server Preparation

SSH into your VPS:

```bash
ssh root@<VPS_IP>
# or
ssh vincent@<VPS_IP>
```

### 3.1 Install Docker

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
apt install -y docker.io docker-compose-plugin

# Allow non-root Docker usage (if not using root)
usermod -aG docker vincent
# Log out and back in for this to take effect
```

### 3.2 Verify Docker

```bash
docker --version        # Docker version 24.x+
docker compose version  # Docker Compose v2.x+
```

### 3.3 Open Firewall Ports

```bash
# If using UFW
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

---

## 4. Clone & Configure

### 4.1 Clone the Repository

```bash
cd /home/vincent
git clone <YOUR_REPO_URL> Financial-Valuation-Project
cd Financial-Valuation-Project
```

### 4.2 Verify Deployment Files Exist

```bash
ls deploy/
# Expected: Caddyfile  .env.example  deploy.sh  docker-compose.yml  backend/  frontend/
```

---

## 5. Environment Variables

### 5.1 Create `.env` from Template

```bash
cd deploy
cp .env.example .env
nano .env
```

### 5.2 Required Settings

Edit these values in `.env`:

```bash
# Your actual domain (REQUIRED)
VITE_API_URL=https://platform.yourdomain.com/api
CORS_ORIGINS=["https://platform.yourdomain.com"]

# Production mode
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### 5.3 Optional API Keys (Server-Side Fallbacks)

Users provide their own keys via the frontend Step 1 modal. These are fallbacks:

```bash
# Financial Data
ALPHA_VANTAGE_API_KEY=
FMP_API_KEY=
FRED_API_KEY=
SEC_EDGAR_EMAIL=

# AI Providers (OpenRouter is primary)
OPENROUTER_API_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
```

### 5.4 Update Caddyfile Domain

```bash
# Replace placeholder with your actual domain
sed -i 's/platform.yourdomain.com/YOUR_ACTUAL_DOMAIN/g' Caddyfile
```

**⚠️ Critical**: Both `.env` AND `Caddyfile` must use the same domain.

---

## 6. Build & Deploy

### 6.1 One-Command Deploy

```bash
cd /home/vincent/Financial-Valuation-Project/deploy
chmod +x deploy.sh
./deploy.sh
```

This script will:
1. Create deployment directory at `/home/vincent/app`
2. Copy source code
3. Build Docker images (~5-10 min first time)
4. Start all 3 containers
5. Verify health checks

### 6.2 Monitor Build Progress

The build takes time due to system dependencies (ghostscript, Java, tesseract, poppler). Watch progress:

```bash
# In another terminal
cd deploy && docker compose logs -f
```

### 6.3 Verify Running Containers

```bash
docker compose ps
# Expected: 3 containers (backend, frontend, caddy) — all "Up" and "healthy"
```

---

## 7. DNS & SSL

### 7.1 Configure DNS

At your domain registrar, add an **A Record**:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | platform | `<VPS_PUBLIC_IP>` | 300 |

### 7.2 Verify DNS Propagation

```bash
# From your local machine
nslookup platform.yourdomain.com
# or
dig platform.yourdomain.com +short
# Expected: <VPS_PUBLIC_IP>
```

### 7.3 Automatic SSL

Caddy automatically provisions an SSL certificate from Let's Encrypt once DNS resolves. No manual certbot needed.

```bash
# Check Caddy logs for SSL status
docker compose logs caddy | grep -i "certificate\|acme\|tls"
```

---

## 8. Verification

### 8.1 Backend Health (from VPS)

```bash
curl http://localhost:8000/health
# → {"status": "healthy", "version": "2.0.0", ...}

curl http://localhost:8000/health/ready
# → {"status": "ready", ...}
```

### 8.2 Frontend Health (from VPS)

```bash
curl -s http://localhost:3000/ | head -5
# → HTML content (React app)
```

### 8.3 Caddy Reverse Proxy (from VPS)

```bash
curl http://localhost/health
# → {"status": "healthy", ...}
```

### 8.4 HTTPS (from your local machine)

```bash
curl -I https://platform.yourdomain.com/
# → HTTP/2 200, valid SSL certificate
```

### 8.5 Full API Test

```bash
curl -X POST https://platform.yourdomain.com/api/step-1-search \
  -H "Content-Type: application/json" \
  -d '{"query": "AAPL", "market": "international"}'
# → JSON with search results
```

### 8.6 Browser Test

Open `https://platform.yourdomain.com` and walk through the 10-step workflow:
1. Search for "AAPL"
2. Select Apple Inc.
3. Select DCF model
4. Discover peers
5. View required inputs
6. Fetch API data
7. Retrieve historical data
8. Configure forecast drivers
9. Confirm assumptions
10. Run valuation → see results

---

## 9. Updates & Maintenance

### 9.1 Zero-Downtime Update Script

Create on the VPS:

```bash
cat > /home/vincent/update-fingrid.sh << 'EOF'
#!/bin/bash
set -e
cd /home/vincent/Financial-Valuation-Project

git pull

cd deploy

# Build fresh images (old containers keep serving traffic)
docker compose build backend frontend

# Swap in new containers (< 2 seconds downtime)
docker compose up -d --no-deps backend frontend

# Clean up old images
docker system prune -f

echo "✅ FinGrid updated at $(date)"
EOF

chmod +x /home/vincent/update-fingrid.sh
```

### 9.2 Deploy Updates

```bash
ssh vincent@<VPS_IP>
/home/vincent/update-fingrid.sh
```

### 9.3 Common Operations

```bash
cd /home/vincent/Financial-Valuation-Project/deploy

# View status
docker compose ps

# View logs (all)
docker compose logs -f

# View logs (backend only)
docker compose logs -f backend

# View logs (last 50 lines, Caddy)
docker compose logs --tail 50 caddy

# Resource usage
docker stats

# Restart a single service
docker compose restart backend

# Stop everything
docker compose down

# Start everything
docker compose up -d

# Full rebuild (if needed)
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## 10. Troubleshooting

| Problem | Solution |
|---------|----------|
| Backend won't start | `docker compose logs backend` — usually missing env vars or system deps |
| Frontend shows blank page | Check `VITE_API_URL` in `.env` matches your domain exactly |
| SSL certificate fails | Verify DNS A record points to VPS IP; wait 15 min for Let's Encrypt |
| "Connection refused" from API | `docker compose ps` — backend container may be restarting |
| Build fails on `pip install` | Check `requirements.txt`; system deps are in `deploy/backend/Dockerfile` |
| Port 80/443 already in use | `sudo systemctl stop apache2 nginx` to free ports |
| Container exits immediately | `docker compose logs <service>` to see the crash reason |
| CORS errors in browser | Ensure `CORS_ORIGINS` in `.env` includes your exact domain with `https://` |
| API keys not working | Check that users provide keys via Step 1 modal; server keys are fallbacks only |
| Session data lost | Sessions persist to Docker volume at `/app/data`; check `docker volume ls` |

### Debug Commands

```bash
# Enter backend container
docker exec -it fingrid-backend bash

# Check env vars inside container
docker exec fingrid-backend env | grep -i vite

# Check Python packages
docker exec fingrid-backend pip list

# Check if session dir exists
docker exec fingrid-backend ls -la /app/sessions/
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| [`deploy/docker-compose.yml`](docker-compose.yml) | 3-service orchestration |
| [`deploy/backend/Dockerfile`](backend/Dockerfile) | Backend multi-stage build |
| [`deploy/frontend/Dockerfile`](frontend/Dockerfile) | Frontend multi-stage build |
| [`deploy/frontend/nginx.conf`](frontend/nginx.conf) | SPA routing + caching |
| [`deploy/Caddyfile`](Caddyfile) | Reverse proxy + SSL + security |
| [`deploy/.env.example`](.env.example) | Environment variable template |
| [`deploy/deploy.sh`](deploy.sh) | One-command deployment script |
| [`backend/app/core/config.py`](../backend/app/core/config.py) | All backend settings |
| [`frontend/src/services/api.js`](../frontend/src/services/api.js) | Frontend API client |

---

## Architecture Notes

### Session Persistence
- Sessions are saved as JSON files in `backend/sessions/` (mapped to Docker volume `backend_data` at `/app/data`)
- Survives container restarts via Docker volume mount

### API Key Flow
- Users provide their own API keys via the frontend Step 1 modal (stored in `localStorage`)
- Frontend injects keys as HTTP headers (`X-API-Key-*`) on every request
- Backend middleware ([`api_key_middleware.py`](../backend/app/middleware/api_key_middleware.py)) extracts and registers them
- Server-side `.env` keys serve as fallbacks only

### Build-Time Environment Variables
- `VITE_API_URL` is baked into the frontend at **build time** by Vite
- Changing it requires rebuilding the frontend Docker image
- The frontend falls back to `http://localhost:8000/api` if not set (dev mode only)

### No Code Changes Required
- All `localhost` references in the codebase use `import.meta.env.VITE_API_URL` with a localhost fallback — these are only used in development
- The deployment process sets `VITE_API_URL` to your production domain at build time
- No source code modifications are needed for VPS deployment
