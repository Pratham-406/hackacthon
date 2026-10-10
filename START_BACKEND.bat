@echo off
cd /d "%~dp0"
echo ========================================================
echo  SmartPool FastAPI Gateway - Pune-Mumbai Corridor
echo ========================================================
if not exist "backend\.env" (
  echo [Notice] backend\.env not detected.
  echo Copy backend\.env.example to backend\.env to supply Firebase Admin credentials.
  echo Running with persistent local database mode.
)
echo.
echo Installing Python requirements...
py -m pip install -r requirements-demo.txt
if errorlevel 1 (
  echo Python setup failed. Try: python -m pip install -r requirements-demo.txt
  pause
  exit /b 1
)
echo.
echo Starting backend on http://127.0.0.1:8000
py -m uvicorn backend.main:app --reload --port 8000
pause
