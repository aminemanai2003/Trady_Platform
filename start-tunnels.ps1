# ============================================================
#  FX Alpha Platform — Cloudflare Tunnel Launcher (0€)
#  Expose localhost:3000 (Next.js) + localhost:8000 (Django)
#  via trycloudflare.com — aucun compte requis
# ============================================================

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$frontendEnv    = Join-Path $scriptDir "frontend\.env"
$frontendEnvLocal = Join-Path $scriptDir "frontend\.env.local"

# ── Couleurs console ─────────────────────────────────────────
function Write-Header($msg) { Write-Host "`n  $msg" -ForegroundColor Cyan }
function Write-Ok($msg)     { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg)   { Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Write-Err($msg)    { Write-Host "  [ERR] $msg" -ForegroundColor Red }

Clear-Host
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Cyan
Write-Host "    FX Alpha — Cloudflare Tunnel Launcher (trycloudflare.com) " -ForegroundColor Cyan
Write-Host "  ============================================================" -ForegroundColor Cyan

# ── Étape 1 : Vérifier / installer cloudflared ───────────────
Write-Header "Étape 1 — Vérification de cloudflared..."
$cfInstalled = $null
try { $cfInstalled = Get-Command cloudflared -ErrorAction Stop } catch {}

if (-not $cfInstalled) {
    Write-Warn "cloudflared non trouvé. Installation via winget..."
    try {
        winget install Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements
        # Rafraîchir le PATH pour la session courante
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("PATH", "User")
        $cfInstalled = Get-Command cloudflared -ErrorAction Stop
        Write-Ok "cloudflared installé avec succès."
    } catch {
        Write-Err "Impossible d'installer cloudflared automatiquement."
        Write-Host "  Télécharge-le manuellement depuis :" -ForegroundColor Yellow
        Write-Host "  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" -ForegroundColor Yellow
        Read-Host "  Appuie sur Entrée pour quitter"
        exit 1
    }
} else {
    Write-Ok "cloudflared détecté : $($cfInstalled.Source)"
}

# ── Étape 2 : Démarrer les tunnels ───────────────────────────
Write-Header "Étape 2 — Démarrage des tunnels (cela prend ~15 secondes)..."

$logFrontend = Join-Path $env:TEMP "cf_frontend_3000.log"
$logBackend  = Join-Path $env:TEMP "cf_backend_8000.log"

# Nettoyer les anciens logs
Remove-Item $logFrontend -ErrorAction SilentlyContinue
Remove-Item $logBackend  -ErrorAction SilentlyContinue

# Lancer les deux tunnels en arrière-plan
$procFrontend = Start-Process cloudflared `
    -ArgumentList "tunnel --url http://localhost:3000 --no-autoupdate" `
    -RedirectStandardError $logFrontend `
    -WindowStyle Hidden `
    -PassThru

$procBackend = Start-Process cloudflared `
    -ArgumentList "tunnel --url http://localhost:8000 --no-autoupdate" `
    -RedirectStandardError $logBackend `
    -WindowStyle Hidden `
    -PassThru

Write-Host "  Attente des URLs Cloudflare" -NoNewline

# ── Étape 3 : Capturer les URLs ──────────────────────────────
function Wait-ForUrl($logFile, $label) {
    $timeout = 60  # secondes max
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 1
        $elapsed++
        if (Test-Path $logFile) {
            $content = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
            if ($content -match "https://[\w-]+\.trycloudflare\.com") {
                return $Matches[0]
            }
        }
    }
    Write-Err "`n  Timeout : impossible de récupérer l'URL pour $label"
    return $null
}

$urlFrontend = Wait-ForUrl $logFrontend "frontend (port 3000)"
$urlBackend  = Wait-ForUrl $logBackend  "backend (port 8000)"

Write-Host ""

if (-not $urlFrontend -or -not $urlBackend) {
    Write-Err "Échec du démarrage des tunnels. Vérifie que les serveurs tournent :"
    Write-Host "  - Next.js  : npm run dev (port 3000)" -ForegroundColor Yellow
    Write-Host "  - Django   : python manage.py runserver (port 8000)" -ForegroundColor Yellow
    if ($procFrontend) { Stop-Process -Id $procFrontend.Id -ErrorAction SilentlyContinue }
    if ($procBackend)  { Stop-Process -Id $procBackend.Id  -ErrorAction SilentlyContinue }
    Read-Host "  Appuie sur Entrée pour quitter"
    exit 1
}

Write-Ok "Tunnel frontend : $urlFrontend"
Write-Ok "Tunnel backend  : $urlBackend"

# ── Étape 4 : Mettre à jour les .env du frontend ─────────────
Write-Header "Étape 3 — Mise à jour des fichiers .env..."

function Update-EnvFile($path, $replacements) {
    if (-not (Test-Path $path)) {
        Write-Warn "Fichier non trouvé : $path (ignoré)"
        return
    }
    $content = Get-Content $path -Raw
    foreach ($key in $replacements.Keys) {
        $newVal = $replacements[$key]
        # Remplace KEY="ancienne_valeur" ou KEY=ancienne_valeur
        $content = $content -replace "(?m)^($key=).*$", "`${1}$newVal"
    }
    Set-Content $path $content -NoNewline
    Write-Ok "Mis à jour : $([System.IO.Path]::GetFileName($path))"
}

Update-EnvFile $frontendEnv @{
    "NEXTAUTH_URL"                   = $urlFrontend
    "NEXT_PUBLIC_API_URL"            = "$urlBackend/api"
    "CLOUDFLARE_TUNNEL_FRONTEND_URL" = $urlFrontend
    "CLOUDFLARE_TUNNEL_BACKEND_URL"  = $urlBackend
}

Update-EnvFile $frontendEnvLocal @{
    "DJANGO_API_URL"      = $urlBackend
    "NEXT_PUBLIC_API_URL" = "$urlBackend/api"
}

# ── Résumé final ─────────────────────────────────────────────
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host "   Tunnels actifs !                                           " -ForegroundColor Green
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "   Frontend (Next.js) : $urlFrontend" -ForegroundColor White
Write-Host "   Backend  (Django)  : $urlBackend"  -ForegroundColor White
Write-Host "   API REST           : $urlBackend/api/" -ForegroundColor White
Write-Host ""
Write-Host "   IMPORTANT : Ces URLs changent a chaque redemarrage." -ForegroundColor Yellow
Write-Host "   Relance ce script apres chaque redemarrage." -ForegroundColor Yellow
Write-Host ""
Write-Host "   ACTION REQUISE : Redemarre Next.js pour prendre en compte les nouvelles URLs." -ForegroundColor Magenta
Write-Host "   Dans le terminal frontend : CTRL+C, puis npm run dev" -ForegroundColor Magenta
Write-Host ""
Write-Host "   Appuie sur CTRL+C ici pour arreter les tunnels." -ForegroundColor Gray
Write-Host ""

# ── Attendre et gérer l'arrêt propre ─────────────────────────
try {
    while ($true) { Start-Sleep -Seconds 5 }
} finally {
    Write-Host "`n  Arrêt des tunnels..." -ForegroundColor Yellow
    if ($procFrontend -and -not $procFrontend.HasExited) {
        Stop-Process -Id $procFrontend.Id -ErrorAction SilentlyContinue
    }
    if ($procBackend -and -not $procBackend.HasExited) {
        Stop-Process -Id $procBackend.Id -ErrorAction SilentlyContinue
    }

    # Restaurer les .env locaux
    Update-EnvFile $frontendEnv @{
        "NEXTAUTH_URL"                   = "http://localhost:3000"
        "NEXT_PUBLIC_API_URL"            = "http://localhost:8000/api"
        "CLOUDFLARE_TUNNEL_FRONTEND_URL" = ""
        "CLOUDFLARE_TUNNEL_BACKEND_URL"  = ""
    }
    Update-EnvFile $frontendEnvLocal @{
        "DJANGO_API_URL"      = "http://localhost:8000"
        "NEXT_PUBLIC_API_URL" = "http://localhost:8000/api"
    }
    Write-Ok "URLs locales restaurées dans les .env."
}
