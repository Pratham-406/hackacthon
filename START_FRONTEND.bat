@echo off
cd /d "%~dp0frontend"
echo ========================================================
echo  SmartPool React Frontend - Vite Dev Server
echo ========================================================
if not exist ".env" (
  echo [Notice] frontend\.env not detected.
  echo Copy frontend\.env.example to frontend\.env to configure Firebase Authentication.
  echo The app will load with demo mode enabled.
)
echo.
echo Installing JavaScript dependencies...
call npm install
if errorlevel 1 (
  echo Node.js setup failed. Install Node.js from https://nodejs.org/
  pause
  exit /b 1
)
echo.
echo Starting frontend on http://localhost:3000
call npm run dev
pause
