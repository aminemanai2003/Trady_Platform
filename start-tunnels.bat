@echo off
setlocal enabledelayedexpansion
title FX Alpha - Cloudflare Tunnels

echo.
echo =========================================
echo   FX Alpha Platform - Cloudflare Tunnels
echo   (trycloudflare.com - 100%% gratuit)
echo =========================================
echo.

:: Verifier que cloudflared est installe
where cloudflared >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] cloudflared n'est pas installe.
    echo.
    echo Installe-le avec :
    echo   winget install Cloudflare.cloudflared
    echo.
    echo Ou telecharge l'exe sur :
    echo   https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
    echo.
    pause
    exit /b 1
)

echo [1/4] Demarrage du tunnel BACKEND (port 8000)...
set BACKEND_LOG=%TEMP%\cf_backend.log
start /b cloudflared tunnel --url http://localhost:8000 --no-autoupdate > "%BACKEND_LOG%" 2>&1

echo [2/4] Demarrage du tunnel FRONTEND (port 3000)...
set FRONTEND_LOG=%TEMP%\cf_frontend.log
start /b cloudflared tunnel --url http://localhost:3000 --no-autoupdate > "%FRONTEND_LOG%" 2>&1

echo.
echo [3/4] Attente des URLs Cloudflare (15 secondes)...
timeout /t 15 /nobreak >nul

:: Extraire l'URL backend du log
set BACKEND_URL=
for /f "tokens=*" %%a in ('findstr /i "trycloudflare.com" "%BACKEND_LOG%" 2^>nul') do (
    set LINE=%%a
    for /f "tokens=2 delims= " %%b in ("!LINE!") do (
        echo !LINE! | findstr /i "https://" >nul 2>&1
        if !errorlevel! equ 0 (
            for %%c in (!LINE!) do (
                echo %%c | findstr /i "trycloudflare" >nul 2>&1
                if !errorlevel! equ 0 set BACKEND_URL=%%c
            )
        )
    )
)

:: Extraire l'URL frontend du log
set FRONTEND_URL=
for /f "tokens=*" %%a in ('findstr /i "trycloudflare.com" "%FRONTEND_LOG%" 2^>nul') do (
    set LINE=%%a
    for %%c in (!LINE!) do (
        echo %%c | findstr /i "trycloudflare" >nul 2>&1
        if !errorlevel! equ 0 set FRONTEND_URL=%%c
    )
)

:: Fallback: lire toutes les lignes et trouver les URLs
if "!BACKEND_URL!"=="" (
    for /f "tokens=*" %%a in ('type "%BACKEND_LOG%" 2^>nul ^| findstr /i "https://.*trycloudflare"') do (
        set BACKEND_URL=%%a
        for %%w in (!BACKEND_URL!) do (
            echo %%w | findstr "trycloudflare" >nul 2>&1
            if !errorlevel! equ 0 set BACKEND_URL=%%w
        )
    )
)

if "!FRONTEND_URL!"=="" (
    for /f "tokens=*" %%a in ('type "%FRONTEND_LOG%" 2^>nul ^| findstr /i "https://.*trycloudflare"') do (
        set FRONTEND_URL=%%a
        for %%w in (!FRONTEND_URL!) do (
            echo %%w | findstr "trycloudflare" >nul 2>&1
            if !errorlevel! equ 0 set FRONTEND_URL=%%w
        )
    )
)

echo.
echo =========================================
echo   URLS CLOUDFLARE GENEREES
echo =========================================

if "!BACKEND_URL!"=="" (
    echo [BACKEND]  Non detecte - regarde %BACKEND_LOG%
) else (
    echo [BACKEND]  !BACKEND_URL!
)

if "!FRONTEND_URL!"=="" (
    echo [FRONTEND] Non detecte - regarde %FRONTEND_LOG%
) else (
    echo [FRONTEND] !FRONTEND_URL!
)

echo =========================================
echo.

:: Mettre a jour les fichiers .env si les URLs sont disponibles
if not "!BACKEND_URL!"=="" if not "!FRONTEND_URL!"=="" (
    echo [4/4] Mise a jour des fichiers .env...

    set FRONTEND_ENV=%~dp0frontend\.env
    set FRONTEND_ENV_LOCAL=%~dp0frontend\.env.local
    set BACKEND_ENV=%~dp0backend\.env

    :: Mettre a jour frontend/.env
    powershell -NoProfile -Command ^
        "$content = Get-Content '!FRONTEND_ENV!' -Raw; " ^
        "$content = $content -replace 'NEXTAUTH_URL=.*', 'NEXTAUTH_URL=!FRONTEND_URL!'; " ^
        "$content = $content -replace 'NEXT_PUBLIC_API_URL=.*', 'NEXT_PUBLIC_API_URL=!BACKEND_URL!/api'; " ^
        "$content = $content -replace 'CLOUDFLARE_TUNNEL_FRONTEND_URL=.*', 'CLOUDFLARE_TUNNEL_FRONTEND_URL=!FRONTEND_URL!'; " ^
        "$content = $content -replace 'CLOUDFLARE_TUNNEL_BACKEND_URL=.*', 'CLOUDFLARE_TUNNEL_BACKEND_URL=!BACKEND_URL!'; " ^
        "Set-Content '!FRONTEND_ENV!' $content -NoNewline"

    :: Mettre a jour frontend/.env.local
    powershell -NoProfile -Command ^
        "$content = Get-Content '!FRONTEND_ENV_LOCAL!' -Raw; " ^
        "$content = $content -replace 'DJANGO_API_URL=.*', 'DJANGO_API_URL=!BACKEND_URL!'; " ^
        "$content = $content -replace 'NEXT_PUBLIC_API_URL=.*', 'NEXT_PUBLIC_API_URL=!BACKEND_URL!/api'; " ^
        "$content = $content -replace 'CLOUDFLARE_TUNNEL_FRONTEND_URL=.*', 'CLOUDFLARE_TUNNEL_FRONTEND_URL=!FRONTEND_URL!'; " ^
        "$content = $content -replace 'CLOUDFLARE_TUNNEL_BACKEND_URL=.*', 'CLOUDFLARE_TUNNEL_BACKEND_URL=!BACKEND_URL!'; " ^
        "Set-Content '!FRONTEND_ENV_LOCAL!' $content -NoNewline"

    :: Mettre a jour ALLOWED_HOSTS dans le .env backend si present
    if exist "!BACKEND_ENV!" (
        powershell -NoProfile -Command ^
            "$content = Get-Content '!BACKEND_ENV!' -Raw; " ^
            "$content = $content -replace 'CLOUDFLARE_TUNNEL_FRONTEND_URL=.*', 'CLOUDFLARE_TUNNEL_FRONTEND_URL=!FRONTEND_URL!'; " ^
            "Set-Content '!BACKEND_ENV!' $content -NoNewline"
    )

    echo.
    echo [OK] Fichiers .env mis a jour avec les nouvelles URLs.
    echo.
    echo IMPORTANT : Redemarrez le serveur Next.js pour appliquer les nouvelles URLs :
    echo   cd frontend ^&^& npm run dev
    echo.
) else (
    echo [4/4] URLs non detectees automatiquement.
    echo.
    echo Mets a jour manuellement frontend/.env :
    echo   NEXTAUTH_URL=^<URL_FRONTEND^>
    echo   NEXT_PUBLIC_API_URL=^<URL_BACKEND^>/api
    echo.
    echo Et frontend/.env.local :
    echo   DJANGO_API_URL=^<URL_BACKEND^>
    echo   NEXT_PUBLIC_API_URL=^<URL_BACKEND^>/api
    echo.
)

echo =========================================
echo   Les tunnels tournent en arriere-plan.
echo   Ferme cette fenetre pour les arreter.
echo =========================================
echo.
pause
