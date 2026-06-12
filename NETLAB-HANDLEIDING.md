# AutoPentest AI — NetLab VM Setup Handleiding

## VM Vereisten

| | Minimum | Aanbevolen |
|--|---------|------------|
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| RAM | 4 GB | 8 GB |
| CPU | 2 cores | 4 cores |
| Opslag | 20 GB | 40 GB |
| Netwerk | NAT of bridged | Bridged |

> **Beperkte VM (< 4GB RAM)?** Draai alleen CyberPulse (zie Stap 6).

---

## Stap 1 — VM Voorbereiden

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git wget nano unzip

# Docker installeren
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Versie controleren
docker --version
docker compose version
```

---

## Stap 2 — Project klonen

```bash
cd ~
git clone https://github.com/<jouw-repo>/autopentest-ai.git
cd autopentest-ai

# Zonder internet: unzip autopentest-ai.zip
```

---

## Stap 3 — .env configureren

```bash
cp .env.example .env
nano .env
```

Minimale schoolomgeving configuratie:

```bash
APP_ENV=development
SECRET_KEY=schoolproject-secret-key-change-this-32chars
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

DATABASE_URL=postgresql+asyncpg://autopentest:school123@postgres:5432/autopentest
POSTGRES_DB=autopentest
POSTGRES_USER=autopentest
POSTGRES_PASSWORD=school123

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Clerk.dev (gratis op https://clerk.dev)
CLERK_SECRET_KEY=sk_test_VERVANG_DIT
CLERK_WEBHOOK_SECRET=whsec_VERVANG_DIT
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_VERVANG_DIT

# Anthropic (gratis credits op https://console.anthropic.com)
ANTHROPIC_API_KEY=sk-ant-VERVANG_DIT
CLAUDE_MODEL=claude-opus-4-20250514

# Stripe (optioneel voor schoolproject, test keys op stripe.com)
STRIPE_SECRET_KEY=sk_test_VERVANG_DIT
STRIPE_WEBHOOK_SECRET=whsec_VERVANG_DIT

SCANNER_IMAGE=autopentest-scanner:latest
SCANNER_NETWORK=autopentest_scanner_net
MAX_SCAN_DURATION_SECONDS=1800
SCAN_CONTAINER_MEMORY_LIMIT=1g
SCAN_CONTAINER_CPU_LIMIT=1

CYBERPULSE_URL=http://cyberpulse-web:7823

NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard
```

---

## Stap 4 — Bouwen en starten

```bash
# Scanner image bouwen
docker build -t autopentest-scanner:latest ./scanner/

# Alle services starten (eerste keer 5-10 min)
docker compose up --build -d

# Logs volgen
docker compose logs -f

# Database migraties (na ~30 seconden)
docker compose exec backend alembic upgrade head

# Status controleren
docker compose ps
```

Verwacht: alle containers "Up (healthy)"

---

## Stap 5 — Toegang

VM IP opzoeken: `hostname -I`

| Service | URL |
|---------|-----|
| Frontend dashboard | http://\<VM-IP\>:3000 |
| Backend API | http://\<VM-IP\>:8000 |
| Swagger docs | http://\<VM-IP\>:8000/docs |
| CyberPulse | http://\<VM-IP\>:7823 |
| Nginx proxy | http://\<VM-IP\>:80 |

---

## Stap 6 — CyberPulse standalone (lichtgewicht)

Als de VM te weinig resources heeft:

```bash
cd cyberpulse

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Web interface
python main.py web
# → http://localhost:7823

# CLI scan
python main.py scan --target 192.168.1.1 --modules m01,m03,m07

# Alle modules
python main.py scan --target example.com --all-modules
```

---

## Stap 7 — Firewall openen (NetLab)

```bash
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 7823/tcp
sudo ufw allow 80/tcp
sudo ufw status
```

---

## Stap 8 — Beheer commando's

```bash
# Stoppen (data bewaard)
docker compose down

# Stoppen + data wissen
docker compose down -v

# Service herstarten
docker compose restart backend

# Logs bekijken
docker compose logs backend worker -f

# Database inspecteren
docker compose exec postgres psql -U autopentest -d autopentest
# \dt  →  alle tabellen
# \q   →  afsluiten

# Redis inspecteren
docker compose exec redis redis-cli
# KEYS *  →  alle keys
```

---

## Veelvoorkomende NetLab-problemen

**"Permission denied" bij Docker:**
```bash
sudo usermod -aG docker $USER && newgrp docker
```

**Geen internet in VM (Docker images offline laden):**
```bash
# Op machine met internet:
docker save postgres:16 | gzip > postgres.tar.gz
docker save redis:7 | gzip > redis.tar.gz

# Op VM:
docker load < postgres.tar.gz
docker load < redis.tar.gz
```

**Poort al in gebruik:**
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

**VM heeft <4GB RAM — resources beperken in docker-compose.yml:**
```yaml
services:
  backend:
    mem_limit: 512m
  worker:
    mem_limit: 512m
  frontend:
    mem_limit: 512m
```

**Clerk auth tijdelijk bypassen voor demo (NOOIT in productie):**
```python
# In backend/app/core/auth.py
async def get_current_user():
    return {"id": "demo-user", "email": "student@school.nl"}
```

---

## Health check

```bash
curl http://localhost:8000/api/health
# Verwacht: {"status": "healthy", "database": "connected", "redis": "connected"}
```

---

## Architectuurdiagram

```
Browser / NetLab Client
        |
   [Nginx :80]
    /         \
[Next.js     [FastAPI
  :3000]       :8000]
                |
          [PostgreSQL]  [Redis]
                |           |
          [Celery Worker + Beat]
                |
    [Docker Scanner Container]
    (Kali Linux + pentesttools)
                |
          [Doelsysteem]

CyberPulse (standalone):
Browser → [Flask :7823] → [20 Modules] → [AI Analyse] → [PDF Rapport]
```
