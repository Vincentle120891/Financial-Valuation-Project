#!/bin/bash

# ============================================================
# Financial Valuation Platform — Dev Launcher
# Starts backend + frontend in tmux sessions
# Usage: ./dev.sh
# ============================================================

SESSION="dev"

# Kill existing session if any
tmux kill-session -t $SESSION 2>/dev/null
tmux new-session -d -s $SESSION

# ─── Backend ─────────────────────────────────────────────────
tmux rename-window -t $SESSION "backend"
tmux send-keys -t $SESSION "cd ~/Financial-Valuation-Project/backend" C-m
tmux send-keys -t $SESSION "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION "pip install -r requirements.txt -q" C-m
tmux send-keys -t $SESSION "uvicorn app.main:app --reload --host 127.0.0.1 --port 8000" C-m

# ─── Frontend ────────────────────────────────────────────────
tmux new-window -t $SESSION -n "frontend"
tmux send-keys -t $SESSION "cd ~/Financial-Valuation-Project/frontend" C-m
tmux send-keys -t $SESSION "npm install --silent" C-m
tmux send-keys -t $SESSION "npm run dev -- --host" C-m

# ─── Attach ──────────────────────────────────────────────────
# Press Ctrl+B then D to detach without stopping servers
tmux attach -t $SESSION
