# CyberPulse — Server Deployment Plan

## Overzicht

Dit document beschrijft hoe je CyberPulse van lokale laptop naar een server/cloud setup migreert.

---

## Architectuur: Server Mode

```
┌──────────────────────────────────┐
│          FRONTEND (Next.js)       │
│   Vercel / Nginx + Node.js       │
│   → NEXT_PUBLIC_BACKEND_URL      │
└──────────┬───────────────────────┘
           │ HTTPS (REST + WebSocket)
┌──────────▼───────────────────────┐
│       BACKEND API (FastAPI)       │
│   Gunicorn/Uvicorn workers       │
│   → PostgreSQL, Redis, Celery    │
└──────────┬───────────────────────┘
           │ Internal HTTP / Queue
┌──────────▼───────────────────────┐
│    SCANNER WORKER (CyberPulse)   │
│   Celery worker met Kali tools   │
│   → Alle 86+ tools lokaal        │
└──────────────────────────────────┘
```

---

## Stap 1: Server Voorbereiden

### Optie A: Dedicated Server / VPS (aanbevolen)
- **OS**: Kali Linux 2024+ of Ubuntu 22.04 met Kali repos
- **Min specs**: 4 CPU cores, 8GB RAM, 50GB SSD
- **Aanbevolen**: 8 CPU cores, 16GB RAM, 100GB SSD

### Optie B: Cloud (AWS/Azure/GCR)
- **Frontend**: Vercel (gratis tier) of AWS CloudFront + S3
- **Backend API**: AWS EC2 t3.medium of Azure B2s
- **Scanner Worker**: AWS EC2 c5.xlarge (spot instances voor kosten)
- **Database**: AWS RDS PostgreSQL / Azure Database for PostgreSQL
- **Redis**: AWS ElastiCache / Azure Cache for Redis

### Kali Tools Installeren
```bash
# Op Ubuntu: Kali repos toevoegen
echo "deb http://http.kali.org/kali kali-rolling main non-free contrib" | \
  sudo tee /etc/apt/sources.list.d/kali.list
wget -q -O - https://archive.kali.org/archive-key.asc | sudo apt-key add -
sudo apt update

# Alle benodigde tools
sudo apt install -y \
  nmap nikto sqlmap gobuster nuclei wpscan masscan hydra john hashcat \
  theharvester amass dnsrecon fierce tshark tcpdump bettercap responder \
  crackmapexec medusa zmap netdiscover arpscan hping3 \
  commix wfuzz arjun binwalk exiftool foremost steghide \
  radare2 objdump strace lynis chkrootkit \
  reaver wash aireplay-ng kismet ettercap-text-only macchanger \
  evil-winrm certipy-ad bloodhound impacket-scripts \
  ropper pdfcrack fcrackzip ophcrack

# Python tools
pip install spiderfoot scapy trivy-python grype hashid pwntools
```

---

## Stap 2: Config Aanpassen

### `cyberpulse/config.py`
```python
# Wijzig van:
LAPTOP_MODE = True

# Naar:
LAPTOP_MODE = False  # Server mode: meer parallel, hogere timeouts
TOOL_MAX_PARALLEL = 8  # Was 3 op laptop
TOOL_DEFAULT_TIMEOUT = 600  # Was 300 op laptop
TOOL_RATE_LIMIT = 10000  # Was 1000 op laptop
```

### `.env` (server)
```env
# Backend API
DATABASE_URL=postgresql+asyncpg://cyberpulse:PASSWORD@db:5432/cyberpulse
REDIS_URL=redis://redis:6379/0
APP_ENV=production
FRONTEND_URL=https://jouw-domein.com

# CyberPulse Scanner
DEEPSEEK_API_KEY=sk-xxx
SHODAN_API_KEY=xxx
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Secrets
SECRET_KEY=genereer-met-openssl-rand-base64-32
CLERK_SECRET_KEY=sk_xxx
STRIPE_SECRET_KEY=sk_xxx
```

---

## Stap 3: Deployment Opties

### Optie A: Docker Compose (eenvoudigst)
```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_BACKEND_URL: https://api.jouw-domein.com/api

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://cyberpulse:pass@db:5432/cyberpulse
      REDIS_URL: redis://redis:6379/0
    depends_on: [db, redis]

  scanner:
    build:
      context: ./cyberpulse
      dockerfile: Dockerfile.scanner
    volumes:
      - scan_data:/app/data/scans
    environment:
      CELERY_BROKER_URL: redis://redis:6379/0
    depends_on: [redis]
    # BELANGRIJK: scanner container heeft Kali tools nodig
    # Gebruik kalilinux/kali-rolling als base image

  db:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: cyberpulse
      POSTGRES_USER: cyberpulse
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt

volumes:
  pgdata:
  scan_data:
```

### Dockerfile.scanner
```dockerfile
FROM kalilinux/kali-rolling

RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    nmap nikto sqlmap gobuster nuclei masscan hydra john \
    theharvester amass dnsrecon tshark crackmapexec \
    && apt-get clean

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
```

### Optie B: Systemd Services (zonder Docker)
```bash
# /etc/systemd/system/cyberpulse-api.service
[Unit]
Description=CyberPulse API
After=network.target postgresql.service redis.service

[Service]
User=cyberpulse
WorkingDirectory=/opt/cyberpulse/cyberpulse
ExecStart=/opt/cyberpulse/.venv/bin/uvicorn web.app:app --host 0.0.0.0 --port 5000 --workers 4
Restart=always
EnvironmentFile=/opt/cyberpulse/.env

[Install]
WantedBy=multi-user.target
```

```bash
# /etc/systemd/system/cyberpulse-backend.service
[Unit]
Description=CyberPulse Backend
After=network.target postgresql.service redis.service

[Service]
User=cyberpulse
WorkingDirectory=/opt/cyberpulse/backend
ExecStart=/opt/cyberpulse/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
EnvironmentFile=/opt/cyberpulse/.env

[Install]
WantedBy=multi-user.target
```

---

## Stap 4: Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/cyberpulse
server {
    listen 80;
    server_name jouw-domein.com api.jouw-domein.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.jouw-domein.com;

    ssl_certificate /etc/letsencrypt/live/jouw-domein.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/jouw-domein.com/privkey.pem;

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Scanner API (intern)
    location /scanner/ {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
    }

    # SSE streams (lange timeouts)
    location /api/scan/ {
        proxy_pass http://localhost:5000;
        proxy_read_timeout 3600s;
        proxy_buffering off;
        proxy_cache off;
    }
}

server {
    listen 443 ssl http2;
    server_name jouw-domein.com;

    ssl_certificate /etc/letsencrypt/live/jouw-domein.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/jouw-domein.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
    }
}
```

---

## Stap 5: SSL met Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d jouw-domein.com -d api.jouw-domein.com
# Auto-renewal
sudo systemctl enable certbot.timer
```

---

## Stap 6: Database Migratie

```bash
cd /opt/cyberpulse/backend
alembic upgrade head
```

---

## Stap 7: Security Hardening

1. **Firewall**: Alleen poort 80, 443 open. Scanner NIET publiek.
2. **User isolation**: `cyberpulse` user zonder sudo
3. **Rate limiting**: Nginx `limit_req` zone
4. **CORS**: Alleen eigen domeinen in `FRONTEND_URL`
5. **API keys**: Allen in environment variables, nooit in code
6. **Disk**: Scans directory met quota (geen disk-filling)
7. **Monitoring**: Prometheus + Grafana of Datadog
8. **Backups**: Dagelijkse PostgreSQL dump naar S3/B2

---

## Stap 8: Celery Worker Setup (voor async scans)

Als je scans niet in een thread wilt maar via een task queue:

```python
# cyberpulse/workers/celery_app.py
from celery import Celery

app = Celery("cyberpulse", broker="redis://localhost:6379/0")

@app.task(bind=True, max_retries=1)
def run_scan_task(self, target, modules, scan_type, **kwargs):
    from engine.scanner import Scanner
    scanner = Scanner(target=target, modules=modules, scan_type=scan_type, **kwargs)
    for event in scanner.run():
        self.update_state(state="PROGRESS", meta=event)
    return {"status": "done"}

@app.task(bind=True)
def run_tool_scan_task(self, target, tool_names, **kwargs):
    from tools.tool_runner import ToolRunner
    runner = ToolRunner()
    results = runner.run_parallel(tool_names, target, max_workers=4)
    return [r.to_dict() for r in results]
```

---

## Kosteninschatting (maandelijks)

| Component | Self-hosted VPS | AWS/Azure |
|-----------|-----------------|-----------|
| Server | €20-40/mo (Hetzner CX31) | €80-150/mo (EC2) |
| Database | Inclusief | €30-50/mo (RDS) |
| Redis | Inclusief | €15-25/mo |
| SSL | Gratis (Let's Encrypt) | Gratis (ACM) |
| Domein | €10/jaar | €10/jaar |
| **Totaal** | **~€25-45/mo** | **~€125-225/mo** |

---

## Checklist voor Go-Live

- [ ] Server provisioned met Kali tools
- [ ] PostgreSQL + Redis draaiend
- [ ] `.env` geconfigureerd met productie-waarden
- [ ] SSL certificaat actief
- [ ] Nginx reverse proxy geconfigureerd
- [ ] `LAPTOP_MODE = False` in config.py
- [ ] Database migraties uitgevoerd
- [ ] Frontend deployed met correcte `NEXT_PUBLIC_BACKEND_URL`
- [ ] Firewall: alleen 80/443 open
- [ ] Health check: `curl https://api.jouw-domein.com/api/health`
- [ ] Tools check: `curl https://api.jouw-domein.com/api/tools/check`
- [ ] Test scan succesvol
- [ ] Monitoring actief
- [ ] Backup schema actief
