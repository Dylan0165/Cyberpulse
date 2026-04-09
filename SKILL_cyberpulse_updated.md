---
name: cyberpulse
description: >
  Volledige projectcontext voor CyberPulse — een privacy-first, AI-aangedreven penetratietestplatform.
  Gebruik deze skill ALTIJD wanneer de gebruiker "cyberpulse", "CyberPulse", "de scanner", "de pentest tool",
  "autopentest" of "autopentest-ai" noemt. Gebruik ook wanneer de gebruiker praat over scanmodules,
  DeepSeek AI analyse, scanresultaten, rapporten, de webinterface, scrapers, bevindingen, risicoscores,
  exploit correlatie, scope validator, module runner, target types, Tauri desktop app, Svelte frontend,
  de roadmap, commercialisering, schooldemo, of andere onderdelen van dit project —
  ook als ze de naam "cyberpulse" niet expliciet noemen.
---

# CyberPulse — Volledige Projectcontext

**Bijgewerkt:** 28 maart 2026

CyberPulse is een **privacy-first, AI-aangedreven penetratietestplatform** gebouwd voor Europese privacystandaarden.
Het project heeft drie lagen:

1. **`/cyberpulse/`** — De standalone pentest engine (Python, FastAPI JSON API, DeepSeek AI, 101 modules)
2. **Tauri desktop app** — De primaire UI: Svelte frontend + Rust/Tauri wrapper + Python backend als sidecar op localhost:7823
3. **`/` (autopentest-ai)** — De SaaS-wrapper (Next.js 14 frontend, FastAPI backend, Stripe, Clerk.dev) — nog in ontwikkeling

Alle code zit in dezelfde repo: `autopentest-ai/`

## Huidige Projectfase (maart 2026)

- **Primaire focus:** Schoolproject → klaarstomen voor schooldemo (2-4 weken)
- **Secundaire focus:** Commercieel product (desktop licentie eerst, SaaS daarna)
- **Desktop app architectuur:** Tauri (Rust) + Svelte frontend communiceert met Python FastAPI backend op localhost:7823
- **web/app.py** is omgebouwd naar een **JSON API** voor Tauri (CORS voor localhost:5173 + tauri://localhost, geen Jinja2 templates meer)
- **ai/analyzer.py** — NIET AANRAKEN tenzij expliciet gevraagd. Werkt stabiel.

## Bekende ontbrekende features (prioriteitsvolgorde)

1. Bevindingen-deduplicatie (findings_deduplicator.py) — kritiek
2. Authenticatie op web interface (API key / token)
3. Rate limiting per module (instelbare delays + 429 backoff)
4. OWASP Top 10 + CWE mapping in rapport
5. Request/response evidence opslaan per bevinding
6. Executive rapport template (report_executive.html)
7. MITRE ATT&CK technique_id in AI output schema
8. Risico-dashboard in Svelte UI (gauge + severity breakdown)
9. False positive markering per bevinding in UI
10. Scan vergelijking (scan_diff.py — nieuw/opgelost/ongewijzigd)

---

## Projectstructuur

```
autopentest-ai/
├── cyberpulse/                      ← Standalone pentest engine
│   ├── main.py                      ← CLI entry point (web / scan / scraper)
│   ├── config.py                    ← Centrale configuratie + 101-module registry
│   ├── requirements.txt
│   ├── engine/
│   │   ├── scanner.py               ← Scan orchestrator (SSE events, exploit correlator)
│   │   ├── module_runner.py         ← Dynamische module loader + target-type filter
│   │   ├── exploit_correlator.py    ← CVE-verrijking (CVSS, CISA KEV, ExploitDB)
│   │   └── scope_validator.py       ← Blokkeert ongeautoriseerde targets
│   ├── modules/
│   │   └── m01.py … m101.py         ← 101 scanmodules, elk met een Scanner class
│   ├── ai/
│   │   ├── analyzer.py              ← DeepSeek V3.2 (OpenAI SDK) + JSON repair  ⚠️ NIET AANRAKEN
│   │   ├── formatter.py             ← Output formatting (web / PDF / CLI)
│   │   └── prompts.py               ← AI prompts (Nederlands, structured JSON output)
│   ├── scraper/
│   │   ├── cve_scraper.py           ← CISA KEV + NVD feeds
│   │   ├── technique_scraper.py     ← MITRE ATT&CK technieken
│   │   ├── tool_scraper.py          ← Security tool updates
│   │   └── scheduler.py             ← APScheduler dagelijkse runs
│   ├── reports/
│   │   ├── generator.py             ← PDF/HTML (WeasyPrint + Jinja2)
│   │   └── templates/report.html
│   ├── web/
│   │   ├── app.py                   ← FastAPI JSON API (voor Tauri Svelte frontend)
│   │   │                               CORS: localhost:5173, tauri://localhost, https://tauri.localhost
│   │   └── static/
│   ├── frontend/                    ← Svelte desktop UI (ingebouwd in Tauri venster)
│   │   ├── src/
│   │   │   ├── App.svelte           ← Root component
│   │   │   ├── routes/
│   │   │   │   ├── Dashboard.svelte     ← Recente scans overzicht
│   │   │   │   ├── NewScan.svelte       ← Nieuwe scan starten
│   │   │   │   ├── ScanProgress.svelte  ← Live scan output
│   │   │   │   ├── Report.svelte        ← Scanrapport weergave
│   │   │   │   └── Settings.svelte      ← Config (API keys, tools, paden)
│   │   │   ├── lib/
│   │   │   │   ├── api.ts           ← fetch() naar localhost:7823
│   │   │   │   └── stores.ts        ← Svelte stores voor state management
│   │   │   └── styles/global.css
│   │   └── package.json
│   └── data/scans/                  ← Lokale scanresultaten per scan_id
│
├── src-tauri/                       ← Tauri/Rust shell (desktop app wrapper)
│   ├── src/main.rs                  ← Tauri entry point, Python sidecar starten/stoppen
│   ├── tauri.conf.json              ← App config (1280x800, minWidth 1024, minHeight 600)
│   └── Cargo.toml
│
├── backend/app/                     ← SaaS backend (FastAPI) — in ontwikkeling
│   ├── core/                        ← config, database (SQLAlchemy), redis, auth (Clerk JWT)
│   ├── models/                      ← user, target, scan, legal (SQLAlchemy)
│   ├── schemas/                     ← Pydantic v2
│   ├── services/                    ← scanner, ai_analysis (Claude), billing (Stripe), audit
│   ├── workers/                     ← Celery (scan_tasks, analysis_tasks)
│   └── api/endpoints/               ← targets, scans, legal, billing, users, reports, websocket
│
├── frontend/src/                    ← Next.js 14 (App Router) — SaaS frontend, in ontwikkeling
│   ├── app/(dashboard)/             ← dashboard, targets, scans, reports, billing, settings
│   ├── components/                  ← sidebar, nda-modal, findings-table, scan-progress
│   ├── hooks/use-scan-websocket.ts
│   └── lib/api.ts
│
├── scanner/                         ← Kali Linux Docker containers
├── nginx/nginx.conf
└── docker-compose.yml
```

---

## Tech Stack

### Standalone CyberPulse Engine (`/cyberpulse/`)
| Component | Technologie |
|-----------|-------------|
| API server | FastAPI + uvicorn (JSON API voor Tauri) |
| AI analyse | DeepSeek V3.2 via OpenAI SDK (`deepseek-chat`) — NIET WIJZIGEN |
| Prompts | Nederlands — structured JSON output |
| PDF reports | WeasyPrint + Jinja2 |
| Scheduling | APScheduler |
| CLI output | Rich (terminal formatting) |
| DNS | dnspython |
| SSL analyse | cryptography + pyOpenSSL |
| WHOIS | python-whois |
| Nmap | python-nmap (socket fallback) |
| JWT analyse | PyJWT |

### Tauri Desktop App
| Component | Technologie |
|-----------|-------------|
| Desktop wrapper | Tauri v1/v2 (Rust) |
| UI framework | Svelte + Vite |
| Communicatie | fetch() naar localhost:7823 |
| Python sidecar | Tauri sidecar: start/stop Python FastAPI automatisch |
| Window | 1280x800, resizable, min 1024x600 |

### SaaS Platform (in ontwikkeling)
| Component | Technologie |
|-----------|-------------|
| Frontend | Next.js 14 (App Router), Tailwind CSS, shadcn/ui |
| Backend | Python FastAPI (async), SQLAlchemy 2.0, Pydantic v2 |
| Queue | Celery + Redis |
| Database | PostgreSQL 16 |
| Auth | Clerk.dev (JWT + JWKS) |
| Payments | Stripe |
| AI | Anthropic Claude (claude-opus-4) |
| Scanner containers | Docker (Kali Linux) |
| WebSocket | FastAPI WebSocket + Redis pub/sub |
| Reverse Proxy | Nginx |

---

## Engine / Scanner (`cyberpulse/engine/`)

### `scanner.py` — `Scanner` class

```python
Scanner(
    target: str,
    modules: list[str],
    scan_type: str = "quick",     # quick | full | custom
    scan_mode: str = "blackbox",  # blackbox | graybox | whitebox
    credentials: dict | None = None,
    target_type: str = "web"      # web | network | api | mobile | desktop
)
```

`scanner.run()` is een generator die events yieldt:
- `scan_start` — scan begint (target, scan_type, scan_mode, total_modules)
- `module_start` — module gaat draaien (module, name, index, total)
- `module_done` — module klaar (findings_count, duration, optioneel `skipped: True`)
- `module_error` — module gefaald (error bericht)
- `log` — informatief bericht
- `scan_complete` — alles klaar (total_findings, report_path)

Na alle modules draait de **ExploitCorrelator** automatisch vóór het opslaan van `scan_data.json`.

`scan_data.json` bevat ook: `target_type`, `scan_mode`, `modules_run`

### `module_runner.py` — `run_module(module_id, target, scan_dir, config)`
- Laadt `modules.m{id}` dynamisch via `importlib`
- Filtert modules op `target_types` (skip als target_type niet matcht)
- `config` dict bevat: `credentials`, `scan_mode`, `target_type`
- Retourneert `ModuleResult` met velden: `success`, `skipped`, `findings`, `duration`, `error`

### `exploit_correlator.py` — `ExploitCorrelator`
- Verrijkt bevindingen met CVSS scores (v3.1 / v3.0 / v2.0)
- Checkt CISA Known Exploited Vulnerabilities (KEV) catalog
- Detecteert publieke exploits via ExploitDB-data
- Upgradet severity automatisch als actieve exploits beschikbaar zijn
- Slaat op als `exploit_correlation.json`

### `scope_validator.py`
- Blokkeert AWS/Azure/GCP metadata endpoints (169.254.169.254)
- Blokkeert link-local ranges (169.254.0.0/16), loopback (127.0.0.0/8)
- Staat subdomeinen van het geautoriseerde target toe

---

## Alle 101 Scanmodules

### Configuratie in `config.py`
```python
QUICK_MODULES = ["01", "02", "03", "07", "08", "11", "09", "17"]
ALL_MODULES   = 01–70 + 91–101  (blackbox)
GRAYBOX_MODULES  = 71–80        (vereisen credentials)
WHITEBOX_MODULES = 81–90        (vereisen SSH/broncode)
```

### Modules 01–20: Core Recon & Web Scanning

| ID  | Naam | Phase | Wat het doet |
|-----|------|-------|--------------|
| 01  | Port Scanning | recon | python-nmap of socket scan, 22 common ports |
| 02  | Service Fingerprinting | recon | Banner grabbing, protocol probes (HTTP/HTTPS/SSH/SMTP/FTP) |
| 03  | DNS Enumeration | recon | dnspython: A/AAAA/MX/NS/TXT/CNAME, zone transfer pogingen |
| 04  | Subdomain Discovery | recon | crt.sh CT-logs + DNS brute force (50+ subdomains) |
| 05  | Technology Detection | recon | Wappalyzer-stijl signatures voor CMS, frameworks, servers |
| 06  | SSL/TLS Analysis | recon | Certificaatvalidatie, protocollen, cipher analyse |
| 07  | WHOIS Lookup | recon | python-whois: registrar, datums, nameservers, DNSSEC |
| 08  | HTTP Header Analysis | vuln_scan | Security headers (HSTS, CSP, X-Frame-Options), info leakage |
| 09  | Directory Enumeration | vuln_scan | Multi-threaded (100+ paden + backups), soft-404 detectie |
| 10  | CVE Vulnerability Check | vuln_scan | Versie-matching tegen lokale CVE feed + NVD patterns |
| 11  | Authentication Testing | vuln_scan | Default credentials, login bypass, rate limiting |
| 12  | XSS Detection | vuln_scan | Reflected/stored XSS, DOM-based, sanitization checks |
| 13  | SQL Injection Testing | vuln_scan | Error-based, blind SQLi, input parameter scanning |
| 14  | Network Services | recon | Service enumeration, misconfiguratie detectie |
| 15  | SMB & LDAP | recon | SMB shares, LDAP anonymous bind |
| 16  | Email Security | recon | SPF, DKIM, DMARC records check |
| 17  | Cloud Exposure | recon | S3/Azure blob/GCS open buckets, cloud metadata |
| 18  | API Testing | vuln_scan | REST/GraphQL, authentication bypass, data exposure |
| 19  | Fuzzing | vuln_scan | Input fuzzing, parameter injection |
| 20  | CMS Scanning | vuln_scan | WordPress/Joomla/Drupal versie + plugins + CVEs |

### Modules 21–40: Active Exploitation

| ID  | Naam | Wat het doet |
|-----|------|--------------|
| 21  | Breach Check | data_exposure — HaveIBeenPwned, credential leaks |
| 22  | Firewall & WAF Detection | recon — WAF fingerprinting, bypass technieken |
| 23  | CORS Misconfiguration | vuln_scan — Origin reflection, wildcard CORS |
| 24  | GraphQL Testing | vuln_scan — Introspection, injection, batching attacks |
| 25  | WebSocket Security | vuln_scan — WS hijacking, injection via WebSocket |
| 26  | Default Credentials | exploitation — Dictionary attack op login formulieren |
| 27  | File Upload Testing | vuln_scan — Unrestricted upload, MIME bypass |
| 28  | SSRF Testing | vuln_scan — Server-Side Request Forgery |
| 29  | XXE Testing | vuln_scan — XML External Entity injection |
| 30  | JWT Token Analysis | vuln_scan — Algorithm confusion, weak secrets, none-alg |
| 31  | OAuth & SAML Testing | vuln_scan — Token leakage, redirect_uri bypass |
| 32  | Directory Traversal & LFI | vuln_scan — Path traversal, local file inclusion |
| 33  | Remote Code Execution | exploitation — RCE payloads, command injection |
| 34  | Privilege Escalation | post — SUID/SGID, sudo misconfigs (web-detectie) |
| 35  | Lateral Movement | post — Internal pivot detectie |
| 36  | Active Directory Recon | recon — AD enumeration, kerberoasting indicators |
| 37  | Kerberos Attacks | exploitation — AS-REP roasting, ticket exploitation |
| 38  | Database Exploitation | exploitation — DB error leakage, schema exposure |
| 39  | Backup File Discovery | recon — .bak, .old, .sql, .zip bestanden |
| 40  | Source Code Leaks | recon — .git, .svn, .env exposed |

### Modules 41–50: Session, Auth & Compliance

| ID  | Naam | Wat het doet |
|-----|------|--------------|
| 41  | Session Management | vuln_scan — Session fixation, predictable tokens |
| 42  | Rate Limiting & DoS | vuln_scan — Brute-force protection, API rate limits |
| 43  | 2FA/MFA Bypass | vuln_scan — OTP reuse, backup codes exposure |
| 44  | Business Logic Flaws | vuln_scan — Price manipulation, workflow bypasses |
| 45  | API Security Deep | vuln_scan — Mass assignment, BOLA/IDOR, sensitive exposure |
| 46  | Subdomain Takeover | vuln_scan — Dangling CNAME → unclaimed services |
| 47  | DNS Zone Transfer | recon — AXFR zone transfer poging |
| 48  | Network Service Security | recon — Telnet/FTP/SNMP misconfiguraties |
| 49  | OWASP Top 10 Compliance | analysis — Mapped check op alle 10 OWASP categorieën |
| 50  | IPv6 Security | recon — IPv6 reachability, AAAA records |

### Modules 51–70: Advanced Exploitation

| ID  | Naam | Wat het doet |
|-----|------|--------------|
| 51  | Evidence & Reporting | reporting — Bewijsverzameling, request/response logging |
| 52  | HTTP Request Smuggling | vuln_scan — CL.TE / TE.CL desync attacks |
| 53  | Web Cache Poisoning | vuln_scan — Cache-key manipulation |
| 54  | Prototype Pollution | vuln_scan — JS object prototype manipulation |
| 55  | Deserialization Testing | vuln_scan — Java/PHP/Python deserialization payloads |
| 56  | SSTI Detection | vuln_scan — Server-Side Template Injection (Jinja2, Twig, etc.) |
| 57  | Clickjacking & UI Redressing | vuln_scan — X-Frame-Options, frame-ancestors check |
| 58  | Open Redirect Testing | vuln_scan — URL redirect via parameter manipulation |
| 59  | HTTP Parameter Pollution | vuln_scan — Duplicate parameter injection |
| 60  | CSP Deep Analysis | vuln_scan — Content Security Policy bypass vectors |
| 61  | Password Policy Analysis | vuln_scan — Weak password requirements, policy bypass |
| 62  | Certificate Transparency | recon — CT-log mining voor domein discovery |
| 63  | Threat Intelligence | recon — IP/domain reputatie, AbuseIPDB, VirusTotal |
| 64  | Docker & Container Exposure | recon — Exposed Docker daemon, K8s dashboard |
| 65  | Kubernetes Exposure | recon — K8s API, etcd, dashboard toegang |
| 66  | Serverless Functions | recon — AWS Lambda/Azure Functions discovery |
| 67  | Third-Party Script Analysis | vuln_scan — Externe scripts, CDN integriteit |
| 68  | Mobile API Detection | recon — Mobile-specific endpoints, API keys in responses |
| 69  | CI/CD Pipeline Exposure | recon — Jenkins, GitLab CI, GitHub Actions exposure |
| 70  | Dependency Confusion | vuln_scan — Package namespace attacks |

### Modules 71–80: Gray-box (vereisen credentials)

| ID  | Naam | Wat het doet |
|-----|------|--------------|
| 71  | Authenticated Web Scanning | vuln_scan — Volledige scan met ingelogde sessie |
| 72  | Authenticated API Testing | vuln_scan — API met token/key |
| 73  | Session & Cookie Audit | vuln_scan — HttpOnly, Secure, SameSite flags |
| 74  | Authenticated CMS Audit | vuln_scan — Admin panel checks, plugin/theme vulns |
| 75  | Database Connectivity | vuln_scan — DB access, schema exposure |
| 76  | Internal Port Scan (Auth) | recon — Interne poorten via authenticated context |
| 77  | Admin Panel Discovery | recon — Admin interfaces, management panels |
| 78  | Privilege Escalation (Auth) | exploitation — Role escalation, IDOR |
| 79  | IDOR / Broken Access Control | vuln_scan — Object reference manipulation |
| 80  | Authenticated File Inclusion | vuln_scan — LFI/RFI met auth context |

### Modules 81–90: White-box (vereisen SSH/broncode)

| ID  | Naam | Wat het doet |
|-----|------|--------------|
| 81  | SSH System Audit (Lynis) | audit — Lynis hardening score |
| 82  | Source Code SAST | audit — Statische analyse van broncode |
| 83  | Config File Audit | audit — Geconfigureerde secrets, hardcoded creds |
| 84  | Dependency Vulnerability Scan | audit — npm/pip/composer CVE check |
| 85  | Hardcoded Secrets Detection | audit — API keys, passwords in code |
| 86  | File Permissions Audit | audit — World-writable files, SUID |
| 87  | User & Group Account Audit | audit — Ongebruikte accounts, sudo rechten |
| 88  | Running Services Audit | audit — Onnodige services, exposed daemons |
| 89  | Network Configuration Audit | audit — Firewall regels, open poorten |
| 90  | Docker / Container Audit | audit — Container hardening, image vulnerabilities |

### Modules 91–101: Advanced Tooling (externe tools)

| ID   | Naam | Externe tool | Wat het doet |
|------|------|-------------|--------------|
| 91   | Nuclei Template Scanner | nuclei | Critical/high/medium templates, JSONL output |
| 92   | Gobuster Directory Fuzzing | gobuster | Directory discovery met custom wordlists |
| 93   | SQLmap Injection Testing | sqlmap | Geautomatiseerde SQL injection |
| 94   | testssl.sh TLS Audit | testssl.sh | Uitgebreide TLS configuratieaudit |
| 95   | Feroxbuster Recursive Scan | feroxbuster | Recursieve directory enumeratie |
| 96   | Nmap NSE Scripts | nmap | Nmap Scripting Engine |
| 97   | WhatWeb Fingerprinting | whatweb | Webapplicatie fingerprinting |
| 98   | Gitleaks Secrets Scanner | gitleaks | Git repository secrets |
| 98b  | Android APK Analysis | apktool/jadx | APK beveiligingsanalyse |
| 98c  | iOS IPA Analysis | otool/strings | IPA beveiligingsanalyse |
| 99   | Metasploit Auxiliary Scanner | msfconsole | Metasploit auxiliary modules |
| 100  | Shodan API Intelligence | Shodan API | IP/host reconnaissance |
| 101  | Desktop Binary Analysis | pefile/lief | PE/ELF/Mach-O statische analyse (ASLR, DEP, CFG, canaries) |

### Module bestandsstructuur

```python
class Scanner:
    name = "Module Naam"
    phase = "reconnaissance|scanning|exploitation|post|reporting|analysis|discovery|vulnerability_scan|audit"
    description = "..."
    target_types = ["web", "network", "api", "desktop", "mobile"]  # optioneel, voor filtering

    def __init__(self, target: str, output_dir: Path, config: dict):
        # config bevat: credentials, scan_mode, target_type
        ...

    def run(self) -> dict:
        return {"findings": [...], "raw_output": "..."}
```

**Finding structuur:**
```json
{
    "type": "finding_type",
    "severity": "critical|high|medium|low|info",
    "detail": "beschrijving",
    "description": "uitgebreide beschrijving",
    "title": "korte titel",
    "cve": "CVE-XXXX-XXXXX",
    "cwe": "CWE-89",
    "owasp": "A03:2021",
    "technique_id": "T1190",
    "references": ["url1", "url2"],
    "impact": "impact beschrijving",
    "recommendation": "aanbeveling",
    "evidence": {"request": "...", "response": "..."},
    "port": 443,
    "service": "servicenaam"
}
```

*Noot: `cwe`, `owasp`, `technique_id` en `evidence` zijn geplande velden — nog niet volledig geïmplementeerd in alle modules.*

---

## Configuratie (`cyberpulse/config.py`)

```python
# AI
DEEPSEEK_API_KEY          # Verplicht
DEEPSEEK_BASE_URL         # https://api.deepseek.com/v1
DEEPSEEK_MODEL            # deepseek-chat
DEEPSEEK_TEMPERATURE      # 0.3
DEEPSEEK_MAX_TOKENS       # 8192

# Web / API
FLASK_HOST / PORT         # 127.0.0.1:7823 (dev) of 0.0.0.0:7823 (prod)
FLASK_SECRET_KEY

# Scan
SCAN_TIMEOUT              # 28800 seconden
NMAP_TIMING               # T4
MAX_THREADS               # 50
RATE_LIMIT                # 10000

# Tools
SECLISTS_PATH             # /usr/share/seclists
WORDLIST_DIR              # /usr/share/wordlists

# Optionele API's
HIBP_API_KEY / ABUSEIPDB_API_KEY / VIRUSTOTAL_API_KEY / SHODAN_API_KEY

# Scrapers
SCRAPER_ENABLED / SCRAPER_HOUR / SCRAPER_MINUTE
```

---

## AI-analyse Pipeline

**Flow:**
```
scan_data.json
    → ExploitCorrelator (CVSS/KEV verrijking)
    → DeepSeek API (build_streaming_prompt → chat completion)
    → JSON repair als truncated
    → analysis.json opgeslagen
    → formatter.py → web/PDF/CLI output
```

**AI Output schema:**
```json
{
    "samenvatting": {
        "risicoscore": 0-100,
        "niveau": "kritiek|hoog|gemiddeld|laag|veilig"
    },
    "management_samenvatting": "...",
    "bevindingen": [
        {
            "titel": "...", "module": "...", "ernst": "critical|high|medium|low|info",
            "beschrijving": "...", "impact": "...", "aanbeveling": "...",
            "referenties": [], "technique_id": "T1190"
        }
    ],
    "aanbevelingen_prioriteit": [
        {"prioriteit": 1, "actie": "...", "reden": "...", "complexiteit": "laag|gemiddeld|hoog"}
    ],
    "technische_details": "..."
}
```

**Risicoscore bands:** ≥80 kritiek, ≥60 hoog, ≥40 gemiddeld, ≥20 laag, <20 veilig

---

## Rapporten (`reports/generator.py`)

- `generate_pdf(scan_id)` → WeasyPrint HTML → PDF
- Als WeasyPrint niet beschikbaar: HTML pad retourneren
- `_generate_basic_analysis()` voor als DeepSeek niet beschikbaar is:
  - Normaliseert alle finding-veldnamen (`title|type|name` → `titel`, etc.)
  - Berekent risicoscore: critical×20 + high×10 + medium×5
  - Sorteer op ernst, geen cap op 20 bevindingen
  - Bevat ook `cve` veld per bevinding
- **Gepland:** `report_executive.html` — korte management samenvatting (2-3 pagina's)

---

## Web / API Interface (`web/app.py`)

FastAPI JSON API routes (voor Tauri Svelte frontend):

| Method | Route | Beschrijving |
|--------|-------|-------------|
| POST | `/scan/start` | Start scan, retourneert scan_id |
| GET | `/scan/{id}/stream` | SSE stream van scan events |
| GET | `/scan/{id}/report` | JSON rapport data |
| GET | `/scan/{id}/pdf` | PDF download |
| GET | `/scan/{id}/analysis/stream` | SSE AI analyse stream |
| GET | `/api/scans` | JSON lijst recente scans |
| GET/PUT | `/api/settings` | Settings lezen/schrijven |

CORS ingesteld voor: `localhost:5173`, `tauri://localhost`, `https://tauri.localhost`

Scan ID formaat: `YYYYMMDD_HHMMSS_<8hexchars>`
Data locatie: `cyberpulse/data/scans/{scan_id}/`

---

## SaaS Platform — API Endpoints (in ontwikkeling)

Vereisen Clerk JWT authenticatie:

| Method | Pad | Beschrijving |
|--------|-----|-------------|
| GET/POST | `/api/targets` | Targets beheren |
| POST | `/api/targets/{id}/verify/dns\|file\|ip` | Target verificatie |
| GET/POST | `/api/scans` | Scans beheren |
| POST | `/api/scans/{id}/start\|cancel` | Scan starten/stoppen |
| GET | `/api/scans/{id}/report` | Scanrapport |
| POST | `/api/scans/{id}/share` | Deellink genereren |
| GET | `/api/scans/shared/{token}` | Publiek gedeeld rapport |
| GET/POST | `/api/legal/nda` | NDA beheren |
| GET/POST | `/api/billing/*` | Stripe billing |
| GET | `/api/reports/{id}/pdf\|json\|csv\|xml` | Export formaten |
| WS | `/ws/scan/{id}` | Live scan output |
| WS | `/ws/analysis/{id}` | AI analyse stream |

---

## Commercieel Plan (samenvatting)

### Product versies
- **CyberPulse Desktop** — Tauri desktop app, lokale data, eenmalige licentie (€49-149 + €49/jaar updates)
- **CyberPulse Cloud** — SaaS abonnement (€99-799/maand), teams, compliance rapporten

### Doelgroepen
- Particulieren / freelancers / bug bounty hunters
- MKB zonder eigen security team (NIS2-compliance angle)
- Security consultancies (white-label rapport)
- Enterprise (CI/CD integratie, SIEM, teams)

### Roadmap fasen
1. **Fase 1 (nu):** Schooldemo — kritieke fixes + rapport polish
2. **Fase 2A (1-3 maanden):** Desktop MVP — licentiesysteem, onboarding, white-label
3. **Fase 2B (3-6 maanden):** SaaS — CI/CD plugin, team collaboration, compliance rapporten
4. **Fase 2C (6-12 maanden):** Enterprise — multi-tenant, SOC2, reseller programma

---

## SaaS Billing Plannen (gepland)

| Plan | Prijs | Credits | Targets | Concurrent |
|------|-------|---------|---------|------------|
| Free | €0 | 5/maand | 2 | 1 |
| Solo (desktop) | €49 eenmalig | Onbeperkt | Onbeperkt | 1 |
| Pro (cloud) | €99/maand | 20 | 5 | 1 |
| Business | €299/maand | Onbeperkt | 25 | 3 |
| Enterprise | Op aanvraag | Onbeperkt | Onbeperkt | 10 |

---

## Externe Integraties

| Service | Gebruik | Verplicht |
|---------|---------|-----------|
| DeepSeek API | AI bevindingsanalyse | Ja (standalone) |
| Anthropic Claude | AI analyse (SaaS) | Ja (SaaS) |
| NVD / CISA KEV | CVE data scraper | Nee (auto) |
| crt.sh | Subdomain/CT discovery | Nee |
| Shodan | Host intelligence | Nee (SHODAN_API_KEY) |
| HaveIBeenPwned | Breach check | Nee (HIBP_API_KEY) |
| VirusTotal | Threat intelligence | Nee (VT_API_KEY) |
| AbuseIPDB | IP reputatie | Nee (ABUSEIPDB_API_KEY) |
| Stripe | Betalingen (SaaS) | Ja (SaaS) |
| Clerk.dev | Auth (SaaS) | Ja (SaaS) |

---

## Dataopslag per scan

```
data/scans/{scan_id}/
├── scan_data.json          ← Alle module resultaten + metadata
├── analysis.json           ← DeepSeek AI analyse
├── exploit_correlation.json← CVE/KEV/exploit verrijking
├── findings_status.json    ← (gepland) Bevestigd/FP/Geaccepteerd per bevinding
├── report.html             ← HTML rapport
├── report_executive.html   ← (gepland) Korte management versie
├── report.pdf              ← PDF rapport (als WeasyPrint beschikbaar)
└── {module_id}_*.json      ← Per-module raw output
```

---

## CLI Gebruik

```bash
cd cyberpulse

python main.py web                                    # Start JSON API (poort 7823)
python main.py scan example.nl                        # Snelle scan
python main.py scan example.nl --full                 # Alle 70 blackbox modules
python main.py scan example.nl --modules 01,03,07     # Specifieke modules
python main.py scan example.nl --mode graybox \       # Gray-box met creds
    --username admin --password secret
python main.py scraper                                # Scrapers handmatig draaien
```

---

## Privacy & Security

- Alle data lokaal opgeslagen (desktop versie)
- Geen telemetrie, geen tracking
- Externe verbindingen: DeepSeek API, CISA/NVD/MITRE scrapers
- Scope validator blokkeert cloud metadata endpoints en loopback
- SaaS: Immutable audit trail met SHA-256 hashes, NDA afdwinging, target verificatie
- Docker scanner containers met iptables-scope-beperking
- Geplande toevoeging: verplichte toestemmingsbevestiging per scan (checkbox + audit log)
