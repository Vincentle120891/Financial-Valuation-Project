#!/bin/bash
# ─────────────────────────────────────────────
#  Qwen Coder Session Setup
#  Usage:
#    Start : bash .devcontainer/setup.sh
#    Finish: bash .devcontainer/setup.sh --cleanup
# ─────────────────────────────────────────────

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

cleanup() {
  echo ""
  echo "════════════════════════════════════"
  echo "  Cleanup — freeing kataShared"
  echo "════════════════════════════════════"

  warn "Clearing npm cache..."
  npm cache clean --force 2>/dev/null && log "npm cache cleared"

  warn "Removing node_modules from kataShared..."
  rm -rf /.dockerenv/node_modules && log "node_modules removed"

  warn "Removing npm-cache from kataShared..."
  rm -rf /.dockerenv/npm-cache && log "npm-cache removed"

  warn "Clearing pip cache..."
  pip cache purge 2>/dev/null && log "pip cache cleared" || warn "pip not found, skipping"

  warn "Clearing /tmp..."
  rm -rf /tmp/* 2>/dev/null && log "/tmp cleared"

  AVAIL=$(df -h /.dockerenv | awk 'NR==2 {print $4}')
  echo ""
  log "Done. kataShared available: ${AVAIL}"
  echo "════════════════════════════════════"
  echo ""
}

setup() {
  echo ""
  echo "════════════════════════════════════"
  echo "  Setup — redirecting to kataShared"
  echo "════════════════════════════════════"

  mkdir -p /.dockerenv/npm-cache
  mkdir -p /.dockerenv/node_modules
  log "kataShared dirs created"

  if [ ! -L ./node_modules ]; then
    rm -rf ./node_modules
    ln -s /.dockerenv/node_modules ./node_modules
    log "node_modules → symlinked to kataShared"
  else
    log "node_modules symlink already exists"
  fi

  npm config set cache /.dockerenv/npm-cache
  log "npm cache → /.dockerenv/npm-cache"

  AVAIL=$(df -h /.dockerenv | awk 'NR==2 {print $4}')
  log "kataShared available: ${AVAIL}"
  echo "════════════════════════════════════"
  echo ""
  echo "  Ready. Run: npm install"
  echo ""
}

# ── Entry point ───────────────────────────────
if [[ "${1:-}" == "--cleanup" ]]; then
  cleanup
else
  setup
fi
