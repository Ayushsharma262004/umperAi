#!/bin/bash

# UmpirAI Web Application Startup Script
# This script starts both the backend API and frontend webapp

echo "🏏 Starting UmpirAI Web Application..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

# Install backend dependencies if needed
if [ ! -d "backend/venv" ]; then
    echo "📦 Installing backend dependencies..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# Install frontend dependencies if needed
if [ ! -d "webapp/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd webapp
    npm install
    cd ..
fi

# Start backend in background
echo "🚀 Starting backend API server..."
cd backend
source venv/bin/activate
python api_server.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Start frontend
echo "🌐 Starting frontend development server..."
cd webapp
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ UmpirAI Web Application is running!"
echo ""
echo "📡 Backend API: http://localhost:8000"
echo "🌐 Frontend UI: http://localhost:3000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '👋 Shutting down...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
