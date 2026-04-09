# AutoPentest AI

AI-powered automated penetration testing SaaS platform with legal enforcement, 8-phase scanning, Claude AI analysis, and professional reporting.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Next.js 14  │────▶│  FastAPI      │────▶│ PostgreSQL  │
│  Frontend    │     │  Backend      │     │             │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │   Celery     │────▶ Redis (queue + pub/sub)
                    │   Workers    │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │  Scanner     │  (Kali Linux Docker containers)
                    │  Containers  │
                    └──────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Next.js 14 (App Router), Tailwind CSS, shadcn/ui |
| Backend | Python FastAPI (async), SQLAlchemy 2.0, Pydantic v2 |
| Queue | Celery + Redis |
| Database | PostgreSQL 16 |
| Auth | Clerk.dev (JWT + JWKS) |
| Payments | Stripe (subscriptions + credits) |
| AI | Anthropic Claude (claude-opus-4-20250514) |
| Scanner | Isolated Docker containers (Kali Linux) |
| Reports | WeasyPrint + Jinja2 (PDF), JSON, CSV, XML |
| WebSocket | FastAPI WebSocket + Redis pub/sub |
| Reverse Proxy | Nginx |

## 8 Scan Phases

1. **Reconnaissance** — Nmap, subfinder, httpx, whatweb
2. **Vulnerability Scanning** — Nuclei templates, CVE detection
3. **Web Application Testing** — SQLMap, XSS, directory fuzzing (ffuf)
4. **Network Services** — Service enumeration, misconfiguration detection
5. **Authentication Testing** — Hydra brute-force, credential testing
6. **SSL/TLS & Cryptography** — testssl.sh, certificate analysis
7. **Cloud & Container Security** — Trivy, cloud misconfiguration
8. **OSINT & Secrets** — Gitleaks, theHarvester, data exposure

## Project Structure

```
autopentest-ai/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── env.py
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py
│       │   ├── database.py
│       │   ├── redis.py
│       │   └── auth.py
│       ├── models/
│       │   ├── user.py
│       │   ├── target.py
│       │   ├── scan.py
│       │   └── legal.py
│       ├── schemas/
│       │   ├── target.py
│       │   ├── scan.py
│       │   ├── legal.py
│       │   ├── user.py
│       │   └── report.py
│       ├── legal/
│       │   ├── nda_text.py
│       │   └── verification.py
│       ├── services/
│       │   ├── scanner.py
│       │   ├── ai_analysis.py
│       │   ├── billing.py
│       │   └── audit.py
│       ├── workers/
│       │   ├── celery_app.py
│       │   ├── scan_tasks.py
│       │   └── analysis_tasks.py
│       ├── api/
│       │   └── endpoints/
│       │       ├── targets.py
│       │       ├── scans.py
│       │       ├── legal.py
│       │       ├── billing.py
│       │       ├── users.py
│       │       ├── reports.py
│       │       └── websocket.py
│       └── reports/
│           └── pdf_generator.py
├── scanner/
│   ├── Dockerfile
│   └── scripts/
│       └── entrypoint.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── middleware.ts
│       ├── app/
│       │   ├── globals.css
│       │   ├── layout.tsx
│       │   ├── providers.tsx
│       │   ├── page.tsx  (landing)
│       │   ├── (auth)/
│       │   │   ├── sign-in/[[...sign-in]]/page.tsx
│       │   │   └── sign-up/[[...sign-up]]/page.tsx
│       │   ├── (dashboard)/
│       │   │   ├── layout.tsx
│       │   │   ├── dashboard/page.tsx
│       │   │   ├── targets/page.tsx
│       │   │   ├── targets/[id]/page.tsx
│       │   │   ├── scans/page.tsx
│       │   │   ├── scans/new/page.tsx
│       │   │   ├── scans/[id]/page.tsx
│       │   │   ├── reports/page.tsx
│       │   │   ├── billing/page.tsx
│       │   │   └── settings/page.tsx
│       │   ├── shared/[token]/page.tsx
│       │   └── api/webhooks/
│       │       ├── clerk/route.ts
│       │       └── stripe/route.ts
│       ├── lib/
│       │   ├── utils.ts
│       │   └── api.ts
│       ├── types/
│       │   └── index.ts
│       ├── hooks/
│       │   └── use-scan-websocket.ts
│       └── components/
│           ├── ui/ (button, card, input, progress, badge)
│           ├── layout/ (sidebar, dashboard-layout)
│           ├── legal/ (nda-modal)
│           └── scan/ (scan-progress, findings-table)
└── nginx/
    └── nginx.conf
```

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

### Environment Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Fill in all required values in `.env`:

   | Variable | Description |
   |----------|-------------|
   | `CLERK_SECRET_KEY` | Clerk.dev secret key |
   | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk.dev publishable key |
   | `CLERK_WEBHOOK_SECRET` | Clerk webhook signing secret |
   | `STRIPE_SECRET_KEY` | Stripe secret key |
   | `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
   | `STRIPE_STARTER_PRICE_ID` | Stripe price ID for Starter plan |
   | `STRIPE_PROFESSIONAL_PRICE_ID` | Stripe price ID for Professional plan |
   | `STRIPE_BUSINESS_PRICE_ID` | Stripe price ID for Business plan |
   | `ANTHROPIC_API_KEY` | Anthropic Claude API key |
   | `DATABASE_URL` | PostgreSQL connection string |
   | `REDIS_URL` | Redis connection string |
   | `SECRET_KEY` | Application secret key |

### Running with Docker Compose

```bash
# Build and start all services
docker compose up --build

# Run database migrations
docker compose exec backend alembic upgrade head
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Celery Worker:**
```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

**Celery Beat (scheduled tasks):**
```bash
cd backend
celery -A app.workers.celery_app beat --loglevel=info
```

## Legal & Compliance

- **NDA Enforcement**: Every scan requires explicit NDA acceptance before execution
- **Target Verification**: DNS TXT, file upload, or IP declaration required before scanning
- **Immutable Audit Trail**: All actions logged with SHA-256 hashes, never deletable
- **GDPR Compliant**: Data processing in compliance with EU GDPR
- **Dutch Law**: Governed by laws of the Netherlands
- **Scope Enforcement**: Scanner containers have iptables rules limiting traffic to declared scope only

## Billing Plans

| Plan | Price | Credits/mo | Targets | Concurrent |
|------|-------|-----------|---------|------------|
| Starter | €99/mo | 5 | 3 | 1 |
| Professional | €299/mo | 20 | 15 | 3 |
| Business | €799/mo | Unlimited | Unlimited | 10 |

Additional credits can be purchased separately (5 for €49, 15 for €129, 50 for €399).

## API Endpoints

All endpoints require Clerk JWT authentication unless noted.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/targets` | List targets |
| POST | `/api/targets` | Create target |
| GET | `/api/targets/{id}` | Get target |
| DELETE | `/api/targets/{id}` | Delete target |
| POST | `/api/targets/{id}/verify/dns` | DNS verification |
| POST | `/api/targets/{id}/verify/file` | File verification |
| POST | `/api/targets/{id}/verify/ip` | IP declaration |
| POST | `/api/scans` | Create scan |
| GET | `/api/scans` | List scans |
| GET | `/api/scans/{id}` | Get scan |
| POST | `/api/scans/{id}/start` | Start scan |
| POST | `/api/scans/{id}/cancel` | Cancel scan |
| GET | `/api/scans/{id}/report` | Get scan report |
| POST | `/api/scans/{id}/share` | Generate share link |
| GET | `/api/scans/shared/{token}` | Get shared report (public) |
| GET | `/api/legal/nda` | Get NDA text |
| POST | `/api/legal/nda/accept` | Accept NDA |
| GET | `/api/legal/nda/acceptances` | List acceptances |
| GET | `/api/billing/info` | Billing info |
| POST | `/api/billing/checkout` | Create checkout session |
| POST | `/api/billing/credits` | Purchase credits |
| POST | `/api/billing/cancel` | Cancel subscription |
| GET | `/api/reports/{id}/pdf` | Export PDF |
| GET | `/api/reports/{id}/json` | Export JSON |
| GET | `/api/reports/{id}/csv` | Export CSV |
| GET | `/api/reports/{id}/xml` | Export XML |
| WS | `/ws/scan/{id}` | Live scan output |
| WS | `/ws/analysis/{id}` | AI analysis stream |

## Security

- All scanner containers run in isolated Docker networks with iptables scope enforcement
- Containers are auto-removed after scan completion
- Memory and CPU limits enforced on scanner containers
- Raw scan output stored in Redis with 1-hour TTL (not persisted to database)
- All API routes protected by Clerk JWT verification with JWKS caching
- Stripe webhooks verified with signature validation
- NDA records are immutable with SHA-256 content hashes

## License

Proprietary — All rights reserved.
