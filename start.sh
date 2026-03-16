#!/bin/bash
# Start both backend and frontend for the Short Drama Pipeline prototype

echo "=== Short Drama Translation Pipeline ==="
echo ""

# Start backend
echo "[1/2] Starting backend (port 8001)..."
cd "$(dirname "$0")/backend"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

# Start frontend
echo "[2/2] Starting frontend (port 3001)..."
cd "$(dirname "$0")/frontend"
npx vite --port 3001 &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8001"
echo "Frontend: http://localhost:3001"
echo "API docs: http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop both services."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
