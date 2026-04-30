#!/bin/bash

# Color codes
BACKEND_COLOR='\033[0;36m'    # Cyan for backend
FRONTEND_COLOR='\033[0;32m'   # Green for frontend
NC='\033[0m'                  # No Color
RED='\033[0;31m'

# PIDs
BACKEND_PID=""
FRONTEND_PID=""
CLEANUP_DONE=false

# Cleanup function
cleanup() {
    if [ "$CLEANUP_DONE" = true ]; then
        return
    fi
    CLEANUP_DONE=true
    
    echo -e "\n${RED}Stopping both servers...${NC}"
    if [ -n "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    wait 2>/dev/null
    echo -e "${RED}Both processes stopped.${NC}"
    exit 0
}

# Trap Ctrl+C (SIGINT)
trap cleanup SIGINT SIGTERM

echo -e "${BACKEND_COLOR}Starting FastAPI backend on port 8000...${NC}"
echo -e "${FRONTEND_COLOR}Starting Vite/React frontend on port 3000...${NC}"
echo -e "${NC}Press Ctrl+C to stop both servers.${NC}"
echo ""

# Start backend (FastAPI) on port 8000 with custom commands
(
    echo "Clearing port 8000..."
    fuser -k 8000/tcp 2>/dev/null
    
    # Navigate to the project directory
    cd /home/vincent/Financial-Valuation-Project/backend/
    if [ -f "/home/vincent/.venv/bin/activate" ]; then
        source "/home/vincent/.venv/bin/activate"
    elif [ -f ".venv/bin/activate" ]; then
        source ".venv/bin/activate"
    fi
    pip install -r requirements.txt
    
    # Start the Uvicorn server
    echo "Starting Valuation Agent..."
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) > >(while IFS= read -r line; do echo -e "${BACKEND_COLOR}[BACKEND]${NC} $line"; done) 2>&1 &
BACKEND_PID=$!

# Small delay to let backend start
sleep 1

# Start frontend (Vite/React) on its default port with custom commands
(
    cd /home/vincent/Financial-Valuation-Project/frontend
    
    npm install

    npm audit
    npm audit fix
    npm run build
    npm run dev
) > >(while IFS= read -r line; do echo -e "${FRONTEND_COLOR}[FRONTEND]${NC} $line"; done) 2>&1 &
FRONTEND_PID=$!

# Wait for both processes
wait
