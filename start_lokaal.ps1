$ErrorActionPreference = "Stop"

function Show-Header {
    Clear-Host
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host "    CYBERPULSE / AUTOPENTEST AI - START DASHBOARD      " -ForegroundColor Green
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Check-Env {
    $envPath = Join-Path $PSScriptRoot ".env"
    $envExample = Join-Path $PSScriptRoot ".env.example"
    if (-Not (Test-Path $envPath)) {
        if (Test-Path $envExample) {
            Copy-Item $envExample $envPath
            Write-Host "Geen .env gevonden — .env.example gekopieerd naar .env." -ForegroundColor Yellow
            Write-Host "Vul je API keys in (DeepSeek, Anthropic) in het .env bestand!" -ForegroundColor Yellow
        } else {
            Write-Host "Geen .env of .env.example gevonden." -ForegroundColor Red
        }
        Write-Host "Druk op een toets om door te gaan..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}

function Get-ServiceStatus {
    # CyberPulse engine (port 7823)
    $cpOnline = $false
    try {
        $conn = New-Object System.Net.Sockets.TcpClient
        $conn.Connect("127.0.0.1", 7823)
        $cpOnline = $true
        $conn.Close()
    } catch {}

    # FastAPI backend (port 8000)
    $backendOnline = $false
    try {
        $conn = New-Object System.Net.Sockets.TcpClient
        $conn.Connect("127.0.0.1", 8000)
        $backendOnline = $true
        $conn.Close()
    } catch {}

    # Frontend (port 3000)
    $frontendOnline = $false
    try {
        $conn = New-Object System.Net.Sockets.TcpClient
        $conn.Connect("127.0.0.1", 3000)
        $frontendOnline = $true
        $conn.Close()
    } catch {}

    return @{ cp = $cpOnline; backend = $backendOnline; frontend = $frontendOnline }
}

function Show-Status($status) {
    function StatusLabel($ok) {
        if ($ok) { return "[ONLINE] " } else { return "[OFFLINE]" }
    }
    $cpColor      = if ($status.cp)      { "Green" } else { "DarkGray" }
    $backColor    = if ($status.backend)  { "Green" } else { "DarkGray" }
    $frontColor   = if ($status.frontend) { "Green" } else { "DarkGray" }

    Write-Host " Diensten:"
    Write-Host "   CyberPulse Engine  (port 7823) : " -NoNewline
    Write-Host (StatusLabel $status.cp) -ForegroundColor $cpColor
    Write-Host "   FastAPI Backend     (port 8000) : " -NoNewline
    Write-Host (StatusLabel $status.backend) -ForegroundColor $backColor
    Write-Host "   Next.js Frontend    (port 3000) : " -NoNewline
    Write-Host (StatusLabel $status.frontend) -ForegroundColor $frontColor
    Write-Host ""
}

function Show-Menu {
    Show-Header
    $status = Get-ServiceStatus
    Show-Status $status

    Write-Host " --- DESKTOP APP (Aanbevolen) ---" -ForegroundColor Yellow
    Write-Host "  1.  Start Desktop App (Tauri + CyberPulse engine)"
    Write-Host "  2.  Start ALLEEN CyberPulse engine (achtergrond, port 7823)"
    Write-Host ""
    Write-Host " --- VOLLEDIG DOCKER PLATFORM ---" -ForegroundColor Yellow
    Write-Host "  3.  Start volledig platform (Docker Compose)"
    Write-Host "  4.  Start + opnieuw bouwen (Docker Build)"
    Write-Host "  5.  Stop Docker platform"
    Write-Host ""
    Write-Host " --- LOGS & TOOLS ---" -ForegroundColor Yellow
    Write-Host "  6.  Bekijk Backend logs"
    Write-Host "  7.  Bekijk Frontend logs"
    Write-Host "  8.  Open Next.js frontend  (http://localhost:3000)"
    Write-Host "  9.  Open API documentatie  (http://localhost:8000/api/docs)"
    Write-Host "  10. Open CyberPulse engine (http://localhost:7823/docs)"
    Write-Host "  11. Run database migraties"
    Write-Host ""
    Write-Host "  Q.  Verlaten"
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Start-DesktopApp {
    $desktopScript = Join-Path $PSScriptRoot "cyberpulse\start.ps1"
    if (Test-Path $desktopScript) {
        Write-Host "Desktop app starten via cyberpulse\start.ps1..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$desktopScript`"" -WorkingDirectory (Join-Path $PSScriptRoot "cyberpulse")
        Write-Host "Desktop app wordt geopend in een nieuw venster." -ForegroundColor Green
    } else {
        Write-Host "cyberpulse\start.ps1 niet gevonden!" -ForegroundColor Red
    }
    Start-Sleep -Seconds 2
}

function Start-CyberPulseEngine {
    $cpDir = Join-Path $PSScriptRoot "cyberpulse"
    Write-Host "CyberPulse engine starten op port 7823..." -ForegroundColor Cyan

    # Check Python
    try { python --version | Out-Null } catch {
        Write-Host "Python niet gevonden in PATH!" -ForegroundColor Red
        return
    }

    # Install deps if needed
    $needsPip = $false
    try {
        python -c "import fastapi, uvicorn" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { $needsPip = $true }
    } catch { $needsPip = $true }

    if ($needsPip) {
        Write-Host "Python packages installeren..." -ForegroundColor Yellow
        Push-Location $cpDir
        python -m pip install -r requirements.txt --quiet
        Pop-Location
    }

    # Start in background window
    Start-Process powershell -ArgumentList "-NoExit", "-Command", `
        "Set-Location '$cpDir'; python -m uvicorn web.app:app --host 127.0.0.1 --port 7823 --reload" `
        -WorkingDirectory $cpDir

    Write-Host "Engine gestart in achtergrondvenster op http://localhost:7823" -ForegroundColor Green
    Write-Host "Wacht even totdat de engine online is..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 3
}

# ── Main ────────────────────────────────────────────────────────────
Check-Env

while ($true) {
    Show-Menu
    $choice = Read-Host "Kies een optie (1-11 of Q)"

    switch ($choice) {
        "1" {
            Start-DesktopApp
        }
        "2" {
            Start-CyberPulseEngine
        }
        "3" {
            Write-Host "Docker platform starten..." -ForegroundColor Cyan
            docker compose up -d
            Write-Host "Klaar! Open http://localhost:3000 in je browser." -ForegroundColor Green
            Start-Sleep -Seconds 2
        }
        "4" {
            Write-Host "Docker platform bouwen en starten..." -ForegroundColor Cyan
            docker compose up -d --build
            Write-Host "Klaar!" -ForegroundColor Green
            Start-Sleep -Seconds 2
        }
        "5" {
            Write-Host "Docker platform stoppen..." -ForegroundColor Cyan
            docker compose down
            Write-Host "Klaar!" -ForegroundColor Green
            Start-Sleep -Seconds 2
        }
        "6" {
            Write-Host "Backend logs (CTRL+C om te stoppen):" -ForegroundColor Yellow
            docker compose logs -f backend
        }
        "7" {
            Write-Host "Frontend logs (CTRL+C om te stoppen):" -ForegroundColor Yellow
            docker compose logs -f frontend
        }
        "8" {
            Start-Process "http://localhost:3000"
            Start-Sleep -Seconds 1
        }
        "9" {
            Start-Process "http://localhost:8000/api/docs"
            Start-Sleep -Seconds 1
        }
        "10" {
            Start-Process "http://localhost:7823/docs"
            Start-Sleep -Seconds 1
        }
        "11" {
            Write-Host "Database migraties uitvoeren..." -ForegroundColor Cyan
            docker compose exec backend alembic upgrade head
            Write-Host "Migraties voltooid!" -ForegroundColor Green
            Write-Host "Druk op een toets om door te gaan..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        {"q" -or "Q"} {
            Write-Host "Dashboard afgesloten." -ForegroundColor Green
            exit 0
        }
        default {
            Write-Host "Ongeldige keuze. Probeer opnieuw." -ForegroundColor Red
            Start-Sleep -Seconds 1
        }
    }
}
