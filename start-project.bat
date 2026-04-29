@echo off
title Trady Platform Launcher
cls
echo.
echo  ================================================
echo    Trady Multi-Agent FX Platform - Launcher
echo  ================================================
echo.
echo  Starting Django backend (port 8000)...
echo  Starting Next.js frontend (port 3000)...
echo.

REM --- Backend: Django ---
start "Trady BACKEND - Django :8000" cmd /k "cd /d "%~dp0backend" && "c:\Users\amine\Desktop\Projet DS\.venv\Scripts\activate.bat" && python manage.py runserver 8000"

REM --- Small delay to let backend start first ---
timeout /t 2 /nobreak >nul

REM --- Frontend: Next.js ---
start "Trady FRONTEND - Next.js :3000" cmd /k "cd /d "%~dp0frontend" && npm run dev"

REM --- Open browser after a few seconds ---
timeout /t 6 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo  Both servers are starting in separate windows.
echo  Browser will open at http://localhost:3000
echo.
echo  Press any key to close this launcher...
pause >nul
