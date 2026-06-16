@echo off
title Trady Platform Launcher
cls
echo.
echo  ================================================
echo    Trady Multi-Agent FX Platform - Launcher
echo  ================================================
echo.
echo  Starting Docker data services...
docker compose up -d
if errorlevel 1 (
  echo.
  echo  Docker failed to start. Make sure Docker Desktop is running.
  pause
  exit /b 1
)

echo.
echo  Running Django migrations against Docker Postgres...
pushd "%~dp0backend"
"%~dp0.venv\Scripts\python.exe" manage.py migrate
popd

echo.
echo  Starting Django backend (port 8000)...
start "Trady BACKEND - Django :8000" cmd /k "cd /d ""%~dp0backend"" && ""%~dp0.venv\Scripts\activate.bat"" && python manage.py runserver 127.0.0.1:8000 --noreload"

timeout /t 2 /nobreak >nul

echo  Starting Next.js frontend (port 3000)...
start "Trady FRONTEND - Next.js :3000" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

timeout /t 6 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo  Docker, backend, and frontend are starting.
echo  Browser will open at http://localhost:3000
echo.
pause
