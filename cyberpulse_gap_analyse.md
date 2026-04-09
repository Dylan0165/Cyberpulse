# CyberPulse — Gap Analyse
## Wat mist er nog voor een complete pentest tool?

*Gegenereerd op: 2026-03-17*

---

## Wat je al hebt ✅

Je hebt al een indrukwekkende basis:
- 101 scanmodules (recon → exploitation → audit)
- DeepSeek V3.2 AI analyse met structured JSON output
- Exploit correlator (CVSS + CISA KEV)
- Scope validator
- PDF/HTML rapportgeneratie
- Web interface met SSE streaming
- Target-type filtering (web / network / api / mobile / desktop)
- Gray-box en white-box modi met credential support
- Externe tools integratie (Nuclei, SQLmap, Metasploit, etc.)
- SaaS wrapper (Next.js + FastAPI + Stripe + Clerk)

---

## Categorie 1 — Scan Engine (KRITIEK ontbrekend) 🔴

### 1.1 Bevindingen-deduplicatie
**Probleem:** Als module 09 (directory enum) en module 32 (LFI) allebei `/.env` vinden, staan er twee identieke bevindingen in het rapport. Er is **geen deduplicator**.
**Wat nodig:** Een `findings_deduplicator.py` die op `type + target + port` dedupliceert vóór AI-analyse.

### 1.2 Scan pauzeren en hervatten
**Probleem:** Als een scan halverwege crasht (of je sluit het venster), is alles weg. Er is geen manier om door te gaan waar je gestopt bent.
**Wat nodig:** Scan-state opslaan per module in een `progress.json`, en een `--resume` flag in de CLI.

### 1.3 Bevindingen-verificatie (false positive filter)
**Probleem:** Automatische scanners produceren veel false positives. Er is geen mechanisme om een bevinding automatisch te verifiëren voordat die naar de AI gaat.
**Wat nodig:** Per kritieke bevinding een tweede verificatiepoging (bijv. XSS payload opnieuw sturen, LFI pad opnieuw checken) om te bevestigen dat het echt is.

### 1.4 Rate limiting / throttling per module
**Probleem:** Er is een globale `RATE_LIMIT` config, maar modules sturen requests zo snel als ze kunnen. Veel targets blokkeren je IP bij te agressieve scans.
**Wat nodig:** Per-module instelbare request delays (`request_delay_ms`, `max_requests_per_second`) en exponential backoff bij 429-responses.

### 1.5 Proxy / Burp Suite integratie
**Probleem:** Geen manier om verkeer via een proxy te sturen voor handmatig meekijken of opslaan van bewijs.
**Wat nodig:** `HTTP_PROXY` / `HTTPS_PROXY` config die doorgegeven wordt aan alle modules die `requests` gebruiken.

---

## Categorie 2 — Rapportage (HOOG ontbrekend) 🟠

### 2.1 OWASP Top 10 mapping in rapport
**Probleem:** Bevindingen hebben typen zoals `sqli`, `xss`, maar het rapport mapt deze niet naar OWASP A01, A02, etc.
**Wat nodig:** Een mapping-tabel in `config.py` of `formatter.py` die elke finding type koppelt aan de juiste OWASP categorie, en een "OWASP Coverage" sectie in het rapport.

### 2.2 CWE nummers per bevinding
**Probleem:** Geen CWE (Common Weakness Enumeration) IDs in findings. Dit is standaard in professionele pentestrapportage.
**Wat nodig:** CWE mapping naast CVE, bijv. SQL Injection = CWE-89, XSS = CWE-79.

### 2.3 MITRE ATT&CK mapping
**Probleem:** Je hebt een MITRE scraper maar de technieken worden niet gekoppeld aan bevindingen in het rapport.
**Wat nodig:** `technique_id` veld per finding (bijv. T1190 - Exploit Public-Facing Application) en een ATT&CK matrix sectie in het rapport.

### 2.4 Executive vs. Technisch rapport (twee varianten)
**Probleem:** Het PDF rapport is één ding. Management wil iets anders zien dan de technische engineer.
**Wat nodig:** Twee templates — `report_executive.html` (alleen management samenvatting + top-10 risico's) en `report_technical.html` (alle details, code snippets, bewijs).

### 2.5 Bewijsmateriaal (screenshots + request/response logs)
**Probleem:** Er is geen bewijs bij bevindingen. Een professioneel rapport vereist request/response bewijs.
**Wat nodig:** Elke bevinding zou een `evidence` veld moeten hebben met het HTTP request, de response en (optioneel) screenshot bewijs.

### 2.6 Vergelijkende rapportage (baseline vs. huidige scan)
**Probleem:** Je kunt niet zien of bevindingen nieuw zijn of al bekend waren van vorige scan.
**Wat nodig:** `scan_diff.py` die twee `scan_data.json` vergelijkt en **nieuw / opgelost / ongewijzigd** labelt.

---

## Categorie 3 — Web Interface & UX (MIDDEL ontbrekend) 🟡

### 3.1 Authenticatie op de web interface
**Probleem:** `web/app.py` heeft geen login. Iedereen met toegang tot poort 7823 kan scans starten.
**Wat nodig:** Een simpele HTTP Basic Auth of token-based login, zeker als de interface ook extern bereikbaar is.

### 3.2 False positive markering in UI
**Probleem:** Je kunt een bevinding niet als "false positive" of "accepted risk" markeren in de UI.
**Wat nodig:** Per bevinding een status-knop (Bevestigd / False Positive / Geaccepteerd risico) die opgeslagen wordt in een `findings_status.json`.

### 3.3 Scan scheduling in de UI
**Probleem:** Er is een APScheduler voor de scrapers, maar je kunt geen scans inplannen via de UI.
**Wat nodig:** Een "Plan scan" functie in de webinterface (bijv. "elke maandag 02:00") die APScheduler gebruikt.

### 3.4 Live findings tabel tijdens scan
**Probleem:** De SSE stream toont module voortgang maar geen individuele bevindingen in real-time.
**Wat nodig:** Module events uitbreiden met `findings` data zodat de UI al een live tabel kan tonen terwijl de scan loopt.

### 3.5 Module configuratie in UI
**Probleem:** Je kunt modules kiezen maar niet configureren (bijv. wordlist kiezen, max threads instellen, custom headers).
**Wat nodig:** Per-module instelbare parameters die via de UI ingevoerd kunnen worden.

---

## Categorie 4 — Modules (SPECIFIEKE GATEN) 🟡

### 4.1 Geen echte XSS payload verificatie
Modules bevatten XSS-detectie maar zonder een headless browser (bijv. Playwright/Selenium) kan reflected XSS niet echt bewezen worden.
**Wat nodig:** Optionele Playwright integratie voor DOM-based XSS verificatie.

### 4.2 Geen DAST voor JavaScript-heavy apps
Single Page Apps (React/Vue/Angular) worden niet goed gescand omdat de HTML leeg is zonder JavaScript executie.
**Wat nodig:** Optionele headless browser modus voor modules die JS-rendered content nodig hebben.

### 4.3 Geen netwerk-level MITM testen
Er is geen module voor ARP poisoning, SSL stripping, of HSTS bypass testen op netwerkniveau.
**Wat nodig:** Alleen relevant voor internal network pentesting, maar zou module 91+ kunnen zijn.

### 4.4 API schema (OpenAPI/Swagger) import
**Probleem:** De API testing modules scrapen endpoints blind. Als je een Swagger/OpenAPI spec hebt, kun je veel gerichter testen.
**Wat nodig:** `--openapi-spec URL` parameter die het schema laadt en alle endpoints + parameters automatisch test.

### 4.5 Authenticated scan via cookie/session token
**Probleem:** Gray-box modules verwachten username+password, maar veel moderne apps gebruiken JWT/OAuth tokens.
**Wat nodig:** `--cookie "session=abc123"` of `--bearer-token "eyJ..."` parameter naast username/password.

---

## Categorie 5 — Infrastructuur & Deployment 🟡

### 5.1 Docker image voor de standalone tool
**Probleem:** Er zijn Docker containers voor de SaaS scanner maar niet voor de standalone `cyberpulse/` tool zelf.
**Wat nodig:** `cyberpulse/Dockerfile` zodat je de tool start met `docker run cyberpulse scan example.nl`.

### 5.2 Installatie-script
**Probleem:** Geen eenvoudige manier om alle externe tools (nmap, nuclei, sqlmap, gobuster, etc.) te installeren.
**Wat nodig:** `install.sh` script dat alle dependencies installeert op Kali/Ubuntu.

### 5.3 Notifications bij scan completion
**Probleem:** Geen manier om een melding te krijgen als een scan (die uren duurt) klaar is.
**Wat nodig:** Webhook / email notificatie bij `scan_complete` event, configureerbaar via `NOTIFY_WEBHOOK_URL` in `.env`.

### 5.4 API key rotatie en veilige opslag
**Probleem:** API keys (DeepSeek, Shodan, etc.) staan plat in `.env`. Geen rotatie-mechanisme.
**Wat nodig:** Ondersteuning voor environment variabelen via `.env` is prima, maar een waarschuwing als `.env` world-readable is zou helpen.

---

## Categorie 6 — AI Analyse Verbeteringen 🟡

### 6.1 AI kan niet doorvragen
**Probleem:** De AI analyse is eenmalig. Als de analyse zegt "SQL injection op /login", kun je niet vragen "geef me de exacte payload".
**Wat nodig:** Een follow-up chat interface naast het rapport waar je de AI over de scan kunt bevragen.

### 6.2 Geen AI-gestuurde prioritering van vervolgstappen
**Probleem:** De AI geeft aanbevelingen maar geen concreet "doe dit eerst, dan dit" stappenplan op basis van beschikbare exploits.
**Wat nodig:** Een "Aanvalspad simulatie" sectie in de AI prompt die exploit chains beschrijft.

### 6.3 AI context is beperkt bij grote scans
**Probleem:** Bij een full scan met 70+ modules en honderden bevindingen zit je snel tegen de 8192 token limiet aan van DeepSeek.
**Wat nodig:** Bevindingen pre-filteren vóór de AI prompt (alleen critical/high), of gebruik maken van chunking.

### 6.4 Geen AI-gegenereerde PoC payloads
**Probleem:** De AI beschrijft een bevinding maar geeft geen concrete proof-of-concept payload.
**Wat nodig:** Per bevinding een optioneel `poc_payload` veld dat de AI kan genereren.

---

## Samenvatting: Prioriteitenlijst

| Prioriteit | Item | Categorie | Complexiteit |
|-----------|------|-----------|-------------|
| 🔴 P1 | Bevindingen-deduplicatie | Engine | Laag |
| 🔴 P1 | Rate limiting per module | Engine | Middel |
| 🔴 P1 | Authenticatie web interface | Security | Laag |
| 🟠 P2 | OWASP Top 10 mapping in rapport | Rapportage | Laag |
| 🟠 P2 | CWE nummers per bevinding | Rapportage | Laag |
| 🟠 P2 | Bewijsmateriaal (request/response logs) | Rapportage | Middel |
| 🟠 P2 | False positive markering | UX | Middel |
| 🟠 P2 | Scan pauzeren/hervatten | Engine | Hoog |
| 🟡 P3 | MITRE ATT&CK mapping | Rapportage | Middel |
| 🟡 P3 | Vergelijkende rapportage (diff) | Rapportage | Middel |
| 🟡 P3 | Scan scheduling in UI | UX | Middel |
| 🟡 P3 | OpenAPI/Swagger spec import | Modules | Middel |
| 🟡 P3 | Cookie/bearer token auth (gray-box) | Modules | Laag |
| 🟡 P3 | Docker image voor standalone tool | Infra | Laag |
| 🟡 P3 | Notificaties bij scan completion | Infra | Laag |
| 🟡 P3 | AI follow-up chat | AI | Hoog |
| 🟡 P3 | Executive vs. technisch rapport | Rapportage | Middel |
