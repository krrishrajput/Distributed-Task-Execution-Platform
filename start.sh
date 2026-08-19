#!/usr/bin/env bash

# TaskStorm — One-Click Development Launcher
# Starts Redis, API Server, 2 Workers, and Frontend Dashboard in a single command.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================================="
echo "⚡ TaskStorm Distributed Task Execution Platform Launcher ⚡"
echo "=========================================================="

# 1. Ensure Redis is running
if ! command -v redis-cli &> /dev/null || ! redis-cli ping &> /dev/null; then
    echo "🔍 Starting Redis service via Homebrew..."
    /opt/homebrew/bin/brew services start redis 2>/dev/null || redis-server --daemonize yes 2>/dev/null || true
    sleep 1
fi

if redis-cli ping &> /dev/null; then
    echo "✅ Redis is running (PONG)"
else
    echo "⚠️ Warning: Could not connect to Redis. Installing/Starting..."
    /opt/homebrew/bin/brew install redis 2>/dev/null || true
    /opt/homebrew/bin/brew services start redis 2>/dev/null || true
fi

# Cleanup background jobs on exit (Ctrl+C)
cleanup() {
    echo ""
    echo "🛑 Shutting down TaskStorm services..."
    kill $(jobs -p) 2>/dev/null || true
    echo "👋 Shutdown complete."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 2. Activate Python Virtual Environment
source "$PROJECT_ROOT/backend/.venv/bin/activate"

# 3. Start Backend API Server in background
echo "🚀 Starting TaskStorm API Server (http://localhost:8000)..."
cd "$PROJECT_ROOT/backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
sleep 2

# 4. Start 2 Worker Processes in background
echo "⚙️ Starting Worker 1..."
python -m app.workers.entry &
WORKER1_PID=$!

echo "⚙️ Starting Worker 2..."
python -m app.workers.entry &
WORKER2_PID=$!

sleep 1

# 5. Start Frontend Dashboard
echo "🎨 Starting Dashboard UI..."
cd "$PROJECT_ROOT/frontend"
npm run dev
