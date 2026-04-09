$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

function Write-Title($text) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
}

function Write-Step($text) {
    Write-Host "  >> $text" -ForegroundColor Yellow
}

function Write-OK($text) {
    Write-Host "  [OK] $text" -ForegroundColor Green
}

function Write-Err($text) {
    Write-Host "  [FOUT] $text" -ForegroundColor Red
}

# .env check
Write-Title "AutoPentest AI - Lokale Dev Setup"

$envPath = Join-Path $ROOT ".env"
$envLocal = Join-Path $ROOT ".env.local.example"

if (-Not (Test-Path $envPath)) {
    if (Test-Path $envLocal) {
        Copy-Item $envLocal $envPath
        Write-Host ""
        Write-Host "  WAARSCHUWING: .env aangemaakt op basis van .env.local.example" -ForegroundColor Yellow
        Write-Host "  Vul je API keys in: $envPath" -ForegroundColor Yellow
        Write-Host "  Druk op een toets om door te gaan..." -ForegroundColor Yellow
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } else {
        Write-Err "Geen .env gevonden. Maak een .env op basis van .env.local.example."
        exit 1
    }
}
Write-OK ".env gevonden"

# Laad .env variabelen in huidige sessie
Get-Content $envPath | Where-Object { $_ -match '^\s*[^#]' -and $_ -match '=' } | ForEach-Object {
    $parts = $_ -split '=', 2
    $key   = $parts[0].Trim()
    $val   = $parts[1].Trim()
    [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
}

# Controleer vereiste tools
Write-Title "Vereisten controleren"

# Python
try {
    $pyVer = python --version 2>&1
    Write-OK "Python: $pyVer"
} catch {
    Write-Err "Python niet gevonden. Installeer van https://python.org"
    exit 1
}

# Node
try {
    $nodeVer = node --version 2>&1
    Write-OK "Node.js: $nodeVer"
} catch {
    Write-Err "Node.js niet gevonden. Installeer van https://nodejs.org"
    exit 1
}

# PostgreSQL
try {
    $pg = psql --version 2>&1
    Write-OK "PostgreSQL: $pg"
} catch {
    Write-Host "  [WAARSCHUWING] psql niet in PATH. Zorg dat PostgreSQL draait op localhost:5432." -ForegroundColor Yellow
    Write-Host "  Download: https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
}

# Redis / Memurai
$redisOk = $false
try {
    $r = redis-cli --version 2>&1
    Write-OK "Redis: $r"
    $redisOk = $true
} catch {
    try {
        $m = memurai-cli --version 2>&1
        Write-OK "Memurai: $m"
        $redisOk = $true
    } catch {
        Write-Host "  [WAARSCHUWING] Redis niet gevonden." -ForegroundColor Yellow
        Write-Host "  Memurai (Windows): https://www.memurai.com/get-memurai" -ForegroundColor Yellow
        Write-Host "  Of via WSL2: sudo apt install redis-server" -ForegroundColor Yellow
    }
}

# Python virtual environment
Write-Title "Backend Python omgeving"

$venvPath = Join-Path $ROOT "backend\.venv"
if (-Not (Test-Path $venvPath)) {
    Write-Step "Virtuele omgeving aanmaken..."
    python -m venv $venvPath
    Write-OK "Venv aangemaakt"
} else {
    Write-OK "Venv bestaat al"
}

$pip = Join-Path $venvPath "Scripts\pip.exe"
Write-Step "Dependencies installeren (kan even duren)..."
& $pip install -r (Join-Path $ROOT "backend\requirements.txt") --quiet
Write-OK "Backend dependencies geinstalleerd"

# Frontend dependencies
Write-Title "Frontend Node dependencies"

$frontendPath = Join-Path $ROOT "frontend"
if (-Not (Test-Path (Join-Path $frontendPath "node_modules"))) {
    Write-Step "npm install uitvoeren..."
    Push-Location $frontendPath
    npm install --silent
    Pop-Location
    Write-OK "Frontend dependencies geinstalleerd"
} else {
    Write-OK "node_modules bestaat al"
}

# Frontend .env.local
$feEnv = Join-Path $frontendPath ".env.local"
if (-Not (Test-Path $feEnv)) {
    Write-Step ".env.local aanmaken voor frontend..."
    $clerkPub  = [System.Environment]::GetEnvironmentVariable("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "Process")
    $stripePub = [System.Environment]::GetEnvironmentVariable("NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY", "Process")
    $backendUrl = [System.Environment]::GetEnvironmentVariable("BACKEND_URL", "Process")
    if (-Not $backendUrl) { $backendUrl = "http://localhost:8000" }
    "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$clerkPub`nNEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=$stripePub`nNEXT_PUBLIC_API_URL=$backendUrl" | Set-Content $feEnv
    Write-OK "frontend/.env.local aangemaakt"
} else {
    Write-OK "frontend/.env.local bestaat al"
}

# Database migraties
Write-Title "Database migraties"
$alembicPython = Join-Path $venvPath "Scripts\python.exe"
Write-Step "Alembic upgrade head..."
try {
    Push-Location (Join-Path $ROOT "backend")
    & $alembicPython -m alembic upgrade head
    Pop-Location
    Write-OK "Migraties uitgevoerd"
} catch {
    Write-Host "  [WAARSCHUWING] Migraties mislukt. Controleer of PostgreSQL draait en .env correct is." -ForegroundColor Yellow
    if ((Get-Location).Path -ne $ROOT) { Pop-Location }
}

# Services starten in aparte vensters
Write-Title "Services starten"

$uvicorn = Join-Path $venvPath "Scripts\uvicorn.exe"
$celery  = Join-Path $venvPath "Scripts\celery.exe"

Write-Step "Backend starten op http://localhost:8000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ROOT\backend'; & '$uvicorn' app.main:app --reload --host 0.0.0.0 --port 8000"

Start-Sleep -Seconds 2

Write-Step "Celery worker starten..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ROOT\backend'; & '$celery' -A app.workers.celery_app worker --loglevel=info --pool=solo"

Start-Sleep -Seconds 1

Write-Step "Frontend starten op http://localhost:3000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ROOT\frontend'; npm run dev"

Write-Title "Klaar!"
Write-Host ""
Write-Host "  Frontend  -> http://localhost:3000" -ForegroundColor Cyan
Write-Host "  Backend   -> http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs  -> http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3 extra vensters geopend (backend, celery, frontend)." -ForegroundColor Gray
Write-Host "  Sluit ze om alles te stoppen." -ForegroundColor Gray
Write-Host ""