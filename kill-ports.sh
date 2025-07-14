#!/bin/bash

# SmartMatch Resume Analyzer - Port Cleanup Script
# Kills all processes running on application ports to prevent conflicts

echo "🔄 Cleaning up SmartMatch Resume Analyzer processes..."

# Define ports used by the application
FRONTEND_PORTS=(3000 3001 3002)
BACKEND_PORTS=(8000 8001 8002)

# Function to kill processes on a specific port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    
    if [ ! -z "$pids" ]; then
        echo "📍 Killing processes on port $port: $pids"
        echo $pids | xargs kill -9 2>/dev/null
        sleep 1
        
        # Verify the port is free
        local remaining=$(lsof -ti:$port 2>/dev/null)
        if [ -z "$remaining" ]; then
            echo "✅ Port $port is now free"
        else
            echo "⚠️  Some processes on port $port may still be running"
        fi
    else
        echo "✅ Port $port is already free"
    fi
}

# Kill frontend ports
echo ""
echo "🎯 Cleaning frontend ports..."
for port in "${FRONTEND_PORTS[@]}"; do
    kill_port $port
done

# Kill backend ports
echo ""
echo "🎯 Cleaning backend ports..."
for port in "${BACKEND_PORTS[@]}"; do
    kill_port $port
done

# Kill any remaining node/npm processes related to the app
echo ""
echo "🎯 Cleaning application processes..."

# Kill npm processes in the project directory
pkill -f "npm.*smart-resume-analyzer" 2>/dev/null && echo "✅ Killed npm processes" || echo "✅ No npm processes found"

# Kill uvicorn processes
pkill -f "uvicorn.*app.main:app" 2>/dev/null && echo "✅ Killed uvicorn processes" || echo "✅ No uvicorn processes found"

# Kill Next.js processes
pkill -f "next.*dev.*turbopack" 2>/dev/null && echo "✅ Killed Next.js processes" || echo "✅ No Next.js processes found"

echo ""
echo "🧹 Cleanup complete! All SmartMatch Resume Analyzer processes have been terminated."
echo "🚀 You can now start the application with clean ports."