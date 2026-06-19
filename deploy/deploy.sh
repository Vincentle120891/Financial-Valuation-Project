#!/bin/bash
# =============================================================================
# FinGrid — EPYCHN-2 Hanoi VPS Deployment Script
# Run this on the VPS after cloning the repo
# =============================================================================

set -e

DEPLOY_DIR="/home/vincent/app"
REPO_DIR="/home/vincent/Financial-Valuation-Project"

echo "========================================="
echo "FinGrid Deployment — EPYCHN-2 Hanoi"
echo "========================================="

# 1. Create deployment directory structure
echo "[1/8] Creating deployment directory..."
mkdir -p "${DEPLOY_DIR}/backend/data"
mkdir -p "${DEPLOY_DIR}/frontend"

# 2. Copy source code to deployment directory
echo "[2/8] Copying source code..."
cp -r "${REPO_DIR}/backend/app" "${DEPLOY_DIR}/backend/"
cp "${REPO_DIR}/backend/requirements.txt" "${DEPLOY_DIR}/backend/"
cp "${REPO_DIR}/deploy/backend/Dockerfile" "${DEPLOY_DIR}/backend/"
cp -r "${REPO_DIR}/frontend/src" "${DEPLOY_DIR}/frontend/"
cp -r "${REPO_DIR}/frontend/public" "${DEPLOY_DIR}/frontend/" 2>/dev/null || true
cp "${REPO_DIR}/frontend/package.json" "${DEPLOY_DIR}/frontend/"
cp "${REPO_DIR}/frontend/package-lock.json" "${DEPLOY_DIR}/frontend/"
cp "${REPO_DIR}/frontend/vite.config.mjs" "${DEPLOY_DIR}/frontend/"
cp "${REPO_DIR}/frontend/tsconfig.json" "${DEPLOY_DIR}/frontend/"
cp "${REPO_DIR}/frontend/index.html" "${DEPLOY_DIR}/frontend/"
cp "${REPO_DIR}/frontend/eslint.config.js" "${DEPLOY_DIR}/frontend/"
cp "${REPO_DIR}/deploy/frontend/Dockerfile" "${DEPLOY_DIR}/frontend/"
cp "${REPO_DIR}/deploy/frontend/nginx.conf" "${DEPLOY_DIR}/frontend/"

# 3. Copy deployment configs
echo "[3/8] Copying deployment configuration..."
cp "${REPO_DIR}/deploy/docker-compose.yml" "${DEPLOY_DIR}/"
cp "${REPO_DIR}/deploy/Caddyfile" "${DEPLOY_DIR}/"

# 4. Create .env from template (only if not exists)
echo "[4/8] Setting up environment..."
if [ ! -f "${DEPLOY_DIR}/.env" ]; then
    cp "${REPO_DIR}/deploy/.env.example" "${DEPLOY_DIR}/.env"
    echo "[!] Created .env from template — EDIT IT with your domain and API keys!"
    echo "    nano ${DEPLOY_DIR}/.env"
    echo ""
    echo "    IMPORTANT: After editing .env, also update the domain in Caddyfile:"
    echo "    sed -i 's/platform.yourdomain.com/YOUR_DOMAIN/g' ${DEPLOY_DIR}/Caddyfile"
else
    echo "[✓] .env already exists, skipping."
fi

# 5. Stop existing containers (if any)
echo "[5/8] Stopping existing containers..."
cd "${DEPLOY_DIR}"
docker compose down --remove-orphans 2>/dev/null || true

# 6. Build and start containers
echo "[6/8] Building and starting containers..."
docker compose build --no-cache
docker compose up -d

# 7. Verify health
echo "[7/8] Verifying deployment..."
sleep 10
docker compose ps
echo ""

# 8. Final status
echo "[8/8] Deployment complete!"
echo ""
echo "========================================="
echo "  Frontend: https://platform.yourdomain.com"
echo "  Backend:  https://platform.yourdomain.com/api"
echo "  Health:   https://platform.yourdomain.com/health"
echo "  Docs:     https://platform.yourdomain.com/docs"
echo ""
echo "  Logs:     cd ${DEPLOY_DIR} && docker compose logs -f"
echo "  Restart:  cd ${DEPLOY_DIR} && docker compose restart"
echo "  Stop:     cd ${DEPLOY_DIR} && docker compose down"
echo "========================================="
