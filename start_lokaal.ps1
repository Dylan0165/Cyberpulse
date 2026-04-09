$ErrorActionPreference = "Stop"

function Show-Header {
    Clear-Host
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host "    🚀 AUTOPENTEST AI - LOKAAL DEV DASHBOARD 🚀       " -ForegroundColor Green
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Check-Env {
    $envPath = Join-Path $PSScriptRoot ".env"
    $envExample = Join-Path $PSScriptRoot ".env.example"
    
    if (-Not (Test-Path $envPath)) {
        if (Test-Path $envExample) {
            Copy-Item $envExample $envPath
            Write-Host "⚠️ Geen .env bestand gevonden. .env.example is gekopieerd naar .env." -ForegroundColor Yellow
            Write-Host "Vul aub je API keys (Clerk, Stripe, Anthropic) in het .env bestand in!" -ForegroundColor Yellow
        } else {
            Write-Host "❌ Geen .env of .env.example gevonden. Dit gaat waarschijnlijk falen." -ForegroundColor Red
        }
        Write-Host "Druk op een toets om door te gaan..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}

function Show-Menu {
    Show-Header
    
    # Check docker status
    $dockerOut = docker compose ps --format json 2>$null
    $isRunning = $false
    if ($dockerOut -match "backend" -or $dockerOut -match "frontend") {
        $isRunning = $true
    }

    Write-Host " Systeem Status: " -NoNewline
    if ($isRunning) {
        Write-Host "[ ONLINE ]" -ForegroundColor Green
    } else {
        Write-Host "[ OFFLINE ]" -ForegroundColor Red
    }
    Write-Host ""

    Write-Host " --- ACTIES ---" -ForegroundColor Yellow
    Write-Host "  1. ▶️  Start Systeem (Docker Compose Up)"
    Write-Host "  2. 🔄  Start Systeem & Bouw opnieuw (Build)"
    Write-Host "  3. ⏹️  Stop Systeem (Docker Compose Down)"
    Write-Host ""
    Write-Host " --- LOGS ---" -ForegroundColor Yellow
    Write-Host "  4. 📋  Bekijk Backend Logs"
    Write-Host "  5. 📋  Bekijk Frontend Logs"
    Write-Host "  6. 📋  Bekijk Celery Worker Logs (Scans)"
    Write-Host ""
    Write-Host " --- APPLICATIE ---" -ForegroundColor Yellow
    Write-Host "  7. 🌍  Open Frontend in Browser (http://localhost:3000)"
    Write-Host "  8. 📖  Open API Documentatie (http://localhost:8000/api/docs)"
    Write-Host "  9. 🛠️  Run Database Migraties"
    Write-Host ""
    Write-Host "  Q. ❌  Verlaten"
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host ""
}

# Main loop
Check-Env

while ($true) {
    Show-Menu
    $choice = Read-Host "Kies een optie (1-9 of Q)"
    
    switch ($choice) {
        "1" {
            Write-Host "Systeem wordt gestart op de achtergrond..." -ForegroundColor Cyan
            docker compose up -d
            Write-Host "Klaar!" -ForegroundColor Green
            Start-Sleep -Seconds 2
        }
        "2" {
            Write-Host "Systeem wordt opnieuw gebouwd en gestart..." -ForegroundColor Cyan
            docker compose up -d --build
            Write-Host "Klaar!" -ForegroundColor Green
            Start-Sleep -Seconds 2
        }
        "3" {
            Write-Host "Systeem wordt gestopt..." -ForegroundColor Cyan
            docker compose down
            Write-Host "Klaar!" -ForegroundColor Green
            Start-Sleep -Seconds 2
        }
        "4" {
            Write-Host "Backend logs (Druk op CTRL+C om te stoppen):" -ForegroundColor Yellow
            docker compose logs -f backend
        }
        "5" {
            Write-Host "Frontend logs (Druk op CTRL+C om te stoppen):" -ForegroundColor Yellow
            docker compose logs -f frontend
        }
        "6" {
            Write-Host "Worker logs (Druk op CTRL+C om te stoppen):" -ForegroundColor Yellow
            docker compose logs -f worker
        }
        "7" {
            Write-Host "Frontend wordt geopend in je browser..." -ForegroundColor Cyan
            Start-Process "http://localhost:3000"
            Start-Sleep -Seconds 1
        }
        "8" {
            Write-Host "Backend API docs worden geopend in je browser..." -ForegroundColor Cyan
            Start-Process "http://localhost:8000/api/docs"
            Start-Sleep -Seconds 1
        }
        "9" {
            Write-Host "Database migraties uitvoeren..." -ForegroundColor Cyan
            docker compose exec backend alembic upgrade head
            Write-Host "Migraties voltooid!" -ForegroundColor Green
            Write-Host "Druk op een toets om door te gaan..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        {"q" -or "Q"} {
            Write-Host "Dashboard afgesloten. Fijne dag!" -ForegroundColor Green
            break
        }
        default {
            Write-Host "Ongeldige keuze. Probeer opnieuw." -ForegroundColor Red
            Start-Sleep -Seconds 1
        }
    }
}
