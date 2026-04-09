# CyberPulse

**Privacy-first penetratietest platform** — een geautomatiseerd beveiligingshulpmiddel met AI-analyse, gebouwd voor Europese privacy-standaarden.

> Alleen gebruiken op systemen waarvoor je expliciete toestemming hebt.

---

## Kenmerken

- **20 scanmodules** — van port scanning tot breach checking
- **AI-analyse** — DeepSeek V3.2 genereert gedetailleerde rapporten in het Nederlands
- **PDF-rapportage** — professionele rapporten via WeasyPrint
- **Live voortgang** — SSE-streaming toont real-time scanresultaten
- **Privacy-first** — geen telemetrie, geen analytics, alleen lokale opslag
- **CLI + Web** — gebruik de terminal of het webinterface
- **Automatische scrapers** — dagelijkse CVE/MITRE/tool updates

## Vereisten

- Python 3.11+
- DeepSeek API-sleutel
- Optioneel: nmap, WeasyPrint (GTK3)

## Installatie

```bash
# Clone of kopieer het project
cd cyberpulse

# Maak een virtuele omgeving
python -m venv venv

# Activeer (Windows)
.\venv\Scripts\Activate.ps1

# Activeer (Linux/Mac)
source venv/bin/activate

# Installeer dependencies
pip install -r requirements.txt
```

## Configuratie

Kopieer `.env.example` naar `.env` en vul je DeepSeek API-sleutel in:

```bash
cp .env.example .env
```

Bewerk `.env`:
```
DEEPSEEK_API_KEY=jouw-api-sleutel-hier
```

## Gebruik

### Webinterface

```bash
python main.py web
```

Open `http://localhost:5000` in je browser.

### CLI Scan

```bash
# Snelle scan (6 modules)
python main.py scan voorbeeld.nl

# Volledige scan (alle 20 modules)
python main.py scan voorbeeld.nl --full

# Specifieke modules
python main.py scan voorbeeld.nl --modules 01 02 06 08
```

### Scrapers draaien

```bash
python main.py scraper
```

## Modules

| ID | Naam | Fase |
|----|------|------|
| M01 | Port Scanning | Reconnaissance |
| M02 | Service Enumeration | Reconnaissance |
| M03 | Web Discovery | Reconnaissance |
| M04 | Web Vulnerabilities | Scanning |
| M05 | Injection Testing | Scanning |
| M06 | Authentication | Scanning |
| M07 | SSL/TLS Audit | Scanning |
| M08 | DNS Reconnaissance | Reconnaissance |
| M09 | Subdomain Enumeration | Reconnaissance |
| M10 | OSINT | Reconnaissance |
| M11 | Headers & Cookies | Scanning |
| M12 | Vulnerability Scan | Scanning |
| M13 | Network Services | Scanning |
| M14 | SMB & LDAP | Scanning |
| M15 | Email Security | Scanning |
| M16 | Cloud Exposure | Reconnaissance |
| M17 | API Testing | Scanning |
| M18 | Fuzzing | Exploitation |
| M19 | CMS Scanning | Scanning |
| M20 | Breach Check | Post |

**Snelle scan** gebruikt modules: M01, M02, M03, M07, M08, M11

## Projectstructuur

```
cyberpulse/
  main.py              # CLI entry point
  config.py            # Configuratie (laadt .env)
  requirements.txt     # Python dependencies
  .env.example         # Voorbeeld configuratie
  engine/
    scanner.py         # Scan orchestrator (SSE events)
    module_runner.py   # Dynamische module loader
  modules/
    m01.py - m20.py    # 20 scanmodules
  ai/
    analyzer.py        # DeepSeek V3.2 integratie
    formatter.py       # Output formatting (web/pdf/cli)
    prompts.py         # AI system/user prompts (Nederlands)
  scraper/
    cve_scraper.py     # CISA KEV + NVD feed
    technique_scraper.py   # MITRE ATT&CK
    tool_scraper.py    # Security tool updates
    scheduler.py       # APScheduler dagelijkse runs
  reports/
    generator.py       # PDF/HTML rapportgenerator
    templates/
      report.html      # Jinja2 template voor rapporten
  web/
    app.py             # Flask applicatie + routes
    static/
      style.css        # Dark terminal theme (pure CSS)
      app.js           # SSE/form handling (vanilla JS)
    templates/
      index.html       # Dashboard + scanformulier
      progress.html    # Live scan voortgang
      report.html      # Web rapport weergave
  data/
    scans/             # Scanresultaten (auto-aangemaakt)
    scraped/           # Scraper data (auto-aangemaakt)
```

## Data & Privacy

- Alle data wordt lokaal opgeslagen onder `data/`
- Er wordt geen data naar externe servers gestuurd, behalve:
  - DeepSeek API voor AI-analyse (scanresultaten worden naar DeepSeek gestuurd)
  - Publieke bronnen voor scrapers (CISA, NVD, MITRE, GitHub)
- Geen tracking, geen cookies, geen analytics
- Rapporten blijven op je eigen systeem

## Disclaimer

Dit hulpmiddel is ontwikkeld voor educatieve doeleinden en geautoriseerde beveiligingstests.
Gebruik het alleen op systemen waarvoor je expliciete toestemming hebt.
Het ongeautoriseerd scannen van systemen is illegaal.

---

*CyberPulse — Gebouwd met focus op privacy en veiligheid.*
