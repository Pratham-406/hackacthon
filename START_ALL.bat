@echo off
cd /d "%~dp0"
echo ========================================================
echo   SmartPool — Starting Backend and Frontend
echo ========================================================
echo.
echo Launching FastAPI backend on http://127.0.0.1:8000 ...
start "SmartPool Backend (FastAPI)" cmd /c "START_BACKEND.bat"

echo Launching Vite frontend on http://localhost:3000 ...
start "SmartPool Frontend (Vite)" cmd /c "START_FRONTEND.bat"

echo.
echo Both services are starting in separate console windows.
echo Frontend: http://localhost:3000
echo Backend:  http://127.0.0.1:8000
echo.
timeout /t 5 >nul
