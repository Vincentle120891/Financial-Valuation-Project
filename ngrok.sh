#!/bin/bash

# ============================================================
# ngrok Tunnel for Financial Valuation Platform
# Exposes the frontend (port 3000) via ngrok so you can
# access the app from your phone or another device.
#
# The Vite dev server proxies /api → localhost:8000, so
# the backend does NOT need a separate tunnel.
#
# Usage:
#   ./ngrok.sh          # Start tunnel (assumes dev servers are running)
#   ./ngrok.sh --setup  # Create frontend/.env then start tunnel
# ============================================================

set -e

FRONTEND_DIR="$(dirname "$0")/frontend"
ENV_FILE="$FRONTEND_DIR/.env"
PORT=3000

# ─── Setup frontend .env ──────────────────────────────────────
setup_env() {
  if [ -f "$ENV_FILE" ]; then
    # Check if VITE_API_URL is already set to /api
    if grep -q "VITE_API_URL=/api" "$ENV_FILE" 2>/dev/null; then
      echo "✅ $ENV_FILE already configured for proxy mode."
    else
      # Backup existing .env
      cp "$ENV_FILE" "${ENV_FILE}.bak"
      echo "# API Configuration" > "$ENV_FILE"
      echo "# Using relative path so API calls go through Vite proxy" >> "$ENV_FILE"
      echo "# This is required for ngrok / remote access" >> "$ENV_FILE"
      echo "VITE_API_URL=/api" >> "$ENV_FILE"
      echo "✅ Updated $ENV_FILE (backup saved as ${ENV_FILE}.bak)"
    fi
  else
    cat > "$ENV_FILE" << 'EOF'
# API Configuration
# Using relative path so API calls go through Vite proxy
# This is required for ngrok / remote access
VITE_API_URL=/api
EOF
    echo "✅ Created $ENV_FILE"
  fi
}

# ─── Main ─────────────────────────────────────────────────────
if [ "$1" = "--setup" ]; then
  setup_env
  echo ""
  echo "⚠️  IMPORTANT: Restart the frontend for the env change to take effect."
  echo "    If using dev.sh, stop it (Ctrl+C) and run it again, or run:"
  echo "    cd frontend && npm run dev -- --host"
  echo ""
  echo "Then run this script again (without --setup) to start the tunnel."
  exit 0
fi

# Auto-setup if .env is missing or not configured
if [ ! -f "$ENV_FILE" ] || ! grep -q "VITE_API_URL=/api" "$ENV_FILE" 2>/dev/null; then
  echo "📦 Setting up frontend .env for proxy mode..."
  setup_env
  echo ""
  echo "⚠️  The frontend .env was just updated."
  echo "    You need to RESTART the frontend dev server for changes to take effect."
  echo ""
  echo "    Quick restart: kill the frontend tmux window, then run:"
  echo "      cd frontend && npm run dev -- --host"
  echo ""
  echo "    After restarting, run this script again to start the tunnel."
  exit 0
fi

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
  echo "❌ ngrok is not installed."
  echo "   Install it: https://ngrok.com/download"
  echo "   Or: snap install ngrok   (Linux)"
  exit 1
fi

# Check if frontend is running
if ! lsof -i :$PORT -sTCP:LISTEN &> /dev/null 2>&1; then
  echo "❌ Frontend is not running on port $PORT."
  echo "   Start it first: ./dev.sh"
  echo "   Or manually:    cd frontend && npm run dev -- --host"
  exit 1
fi

echo "🚀 Starting ngrok tunnel on port $PORT..."
echo "   📱 Open the URL below on your phone."
echo "   ⛔ Press Ctrl+C to stop the tunnel."
echo ""

ngrok http $PORT
