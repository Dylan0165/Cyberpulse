$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

# PATH vernieuwen zodat recent geinstalleerde tools beschikbaar zijn
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")

Clear-Host
Write-Host "================================================" -ForegroundColor White
Write-Host "   CyberPulse v2 - Desktop App" -ForegroundColor White
Write-Host "================================================" -ForegroundColor White
Write-Host ""

# Controleer Python
try {
    $pyVersion = python --version 2>&1
    Write-Host "Python  : $pyVersion" -ForegroundColor DarkGray
} catch {
    Write-Host "FOUT: Python niet gevonden in PATH." -ForegroundColor Red
    exit 1
}

# Controleer Rust/Cargo
try {
    $cargoVersion = cargo --version 2>&1
    Write-Host "Cargo   : $cargoVersion" -ForegroundColor DarkGray
} catch {
    Write-Host ""
    Write-Host "FOUT: Rust/Cargo niet gevonden." -ForegroundColor Red
    Write-Host ""
    Write-Host "  Rust is vereist voor de desktop app (Tauri)." -ForegroundColor Yellow
    Write-Host "  Installeer het eenmalig via:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  https://rustup.rs  ->  download rustup-init.exe  ->  optie 1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Na installatie: sluit deze terminal en start opnieuw." -ForegroundColor Yellow
    Write-Host ""
    Start-Process "https://rustup.rs"
    Read-Host "Druk Enter om te sluiten"
    exit 1
}

# Controleer Node/npm
try {
    $npmVersion = npm --version 2>&1
    Write-Host "npm     : $npmVersion" -ForegroundColor DarkGray
} catch {
    Write-Host "FOUT: npm niet gevonden. Installeer Node.js via https://nodejs.org" -ForegroundColor Red
    exit 1
}

Write-Host ""

# .env aanmaken als die mist
$envFile = Join-Path $ROOT ".env"
if (-Not (Test-Path $envFile)) {
    Write-Host "Geen .env gevonden - aangemaakt. Vul DEEPSEEK_API_KEY in:" -ForegroundColor Yellow
    Write-Host "  $envFile" -ForegroundColor Yellow
    "DEEPSEEK_API_KEY=" | Out-File -FilePath $envFile -Encoding UTF8
    Write-Host ""
}

# [1/3] Python dependencies (alleen als packages missen)
$needsPip = $false
try { python -c "import fastapi, uvicorn" 2>&1 | Out-Null; if ($LASTEXITCODE -ne 0) { $needsPip = $true } } catch { $needsPip = $true }
if ($needsPip) {
    Write-Host "[1/3] Python packages installeren..." -ForegroundColor Cyan
    python -m pip install -r (Join-Path $ROOT "requirements.txt") --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FOUT: pip install mislukt." -ForegroundColor Red
        exit 1
    }
    Write-Host "  OK" -ForegroundColor Green
} else {
    Write-Host "[1/3] Python packages al aanwezig." -ForegroundColor DarkGray
}

# [2/3] npm install
$frontendDir = Join-Path $ROOT "frontend"
if (-Not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "[2/3] npm packages installeren..." -ForegroundColor Cyan
    Push-Location $frontendDir
    npm install --silent
    Pop-Location
    Write-Host "  OK" -ForegroundColor Green
} else {
    Write-Host "[2/3] npm packages al aanwezig." -ForegroundColor DarkGray
}

# [3/3] Tauri desktop app starten
Write-Host "[3/3] Desktop app starten..." -ForegroundColor Cyan
Write-Host ""
Write-Host "  De app opent als een desktop venster." -ForegroundColor Green
Write-Host "  De Python backend start automatisch via Tauri." -ForegroundColor DarkGray
Write-Host "  Sluit het venster om alles te stoppen." -ForegroundColor DarkGray
Write-Host ""

Push-Location (Join-Path $ROOT "src-tauri")
cargo tauri dev
Pop-Location
