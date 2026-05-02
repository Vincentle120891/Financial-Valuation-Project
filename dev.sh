#!/bin/bash

SESSION="dev"

# Kill old session if exists
tmux kill-session -t $SESSION 2>/dev/null

# Start new session
tmux new-session -d -s $SESSION

# Window 1: Backend (Python)
tmux rename-window -t $SESSION "backend"
tmux send-keys -t $SESSION "cd ~/Financial-Valuation-Project" C-m
tmux send-keys -t $SESSION "source venv/bin/activate 2>/dev/null || true" C-m
tmux send-keys -t $SESSION "uvicorn main:app --host 0.0.0.0 --port 8000" C-m

# Window 2: Frontend (Vite)
tmux new-window -t $SESSION -n "frontend"
tmux send-keys -t $SESSION "cd ~/Financial-Valuation-Project" C-m
tmux send-keys -t $SESSION "npm run dev -- --host" C-m

# Attach
tmux attach -t $SESSION
