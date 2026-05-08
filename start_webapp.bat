@echo off
REM UmpirAI Web Application Startup Script for Windows
REM This script starts both the backend API and frontend webapp

echo.
echo 🏏 Starting UmpirAI Web Application...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.10 or higher.
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is not installed. Please install Node.js 18 or higher.
    pause
    exit /b 1
)

REM Install backend dependencies if needed
if not exist "backend\venv" (
    echo 📦 Installing backend dependencies...
    cd backend
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
    cd ..
)

REM Install frontend dependencies if needed
if not exist "webapp\node_modules" (
    echo 📦 Installing frontend dependencies...
    cd webapp
    call npm install
    cd ..
)

REM Start backend in new window
echo 🚀 Starting backend API server...
start "UmpirAI Backend" cmd /k "cd backend && venv\Scripts\activate && python api_server.py"

REM Wait for backend to start
echo ⏳ Waiting for backend to start...
timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo 🌐 Starting frontend development server...
start "UmpirAI Frontend" cmd /k "cd webapp && npm run dev"

echo.
echo ✅ UmpirAI Web Application is starting!
echo.
echo 📡 Backend API: http://localhost:8000
echo 🌐 Frontend UI: http://localhost:3000
echo 📚 API Docs: http://localhost:8000/docs
echo.
echo Two new windows have been opened for backend and frontend.
echo Close those windows to stop the servers.
echo.
pause
