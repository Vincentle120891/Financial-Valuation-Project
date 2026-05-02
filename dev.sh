#!/bin/bash

SESSION="dev"

tmux kill-session -t $SESSION 2>/dev/null
tmux new-session -d -s $SESSION

# Backend
tmux rename-window -t $SESSION "backend"
tmux send-keys -t $SESSION "cd ~/Financial-Valuation-Project" C-m
tmux send-keys -t $SESSION "source venv/bin/activate 2>/dev/null || true" C-m
tmux send-keys -t $SESSION "uvicorn main:app --host 0.0.0.0 --port 8000" C-m

# Frontend
tmux new-window -t $SESSION -n "frontend"
tmux send-keys -t $SESSION "cd ~/Financial-Valuation-Project" C-m
tmux send-keys -t $SESSION "npm run dev -- --host" C-m

# Ngrok backend
tmux new-window -t $SESSION -n "ngrok-backend"
tmux send-keys -t $SESSION "ngrok http 8000" C-m

# Ngrok frontend
tmux new-window -t $SESSION -n "ngrok-frontend"
tmux send-keys -t $SESSION "ngrok http 5173" C-m

tmux attach -t $SESSION
