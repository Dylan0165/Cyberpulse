# CyberPulse — Agent Prompt v2
## Volledig ontwikkelplan — development fase — persoonlijk gebruik

---

## ROL & CONTEXT

Je bent een expert in Python, FastAPI, Rust/Tauri en cybersecurity. Je werkt aan **CyberPulse** — een geautomatiseerd penetratietestplatform dat draait als een **Tauri desktop applicatie**. Het is closed-source, NDA-beschermd en bedoeld voor eigen gebruik tijdens de testfase.

**Doel van dit platform:** Een geautomatiseerde Kali Linux — alle tools draaien vanzelf, de AI analyseert de resultaten en genereert een professioneel rapport. De gebruiker selecteert een target, kiest een scantype en leunt achterover.

**AI-analyse:** DeepSeek API via `deepseek-chat` model. OpenAI-compatible SDK. Bestaande `analyzer.py` blijft intact — niet aanraken tenzij expliciet gevraagd.

**Fase:** Persoonlijke testfase. Geen marketing, geen landing page, geen SaaS. Pure tool.

---

## ARCHITECTUUR OVERZICHT

```
cyberpulse/
├── src-tauri/                  ← Tauri/Rust shell (desktop app wrapper)
│   ├── src/main.rs             ← Tauri entry point, commands, systeem-integratie
│   ├── tauri.conf.json         ← App config, venstergrootte, permissions
│   └── Cargo.toml
│
├── frontend/                   ← Svelte (of React) UI — ingebouwd in Tauri venster
│   ├── src/
│   │   ├── App.svelte          ← Root component
│   │   ├── routes/
│   │   │   ├── Dashboard.svelte     ← Overzicht recente scans
│   │   │   ├── NewScan.svelte       ← Nieuwe scan starten
│   │   │   ├── ScanProgress.svelte  ← Live scan output
│   │   │   ├── Report.svelte        ← Scanrapport
│   │   │   └── Settings.svelte      ← Config (API keys, tools, paden)
│   │   ├── lib/
│   │   │   ├── api.ts          ← Communicatie met Python backend
│   │   │   └── stores.ts       ← Svelte stores voor state
│   │   └── styles/
│   │       └── global.css      ← Design system (zie UI SECTIE)
│   └── package.json
│
├── engine/                     ← Python backend (FastAPI, lokaal)
│   ├── main.py                 ← FastAPI app + startup
│   ├── config.py               ← Config via .env
│   ├── scanner.py              ← Scan orchestrator
│   ├── module_runner.py        ← Dynamische module loader
│   ├── modules/                ← m01.py … m100.py
│   ├── ai/
│   │   ├── analyzer.py         ← DeepSeek integratie (NIET WIJZIGEN)
│   │   ├── formatter.py
│   │   └── prompts.py
│   ├── reports/
│   │   ├── generator.py        ← PDF + HTML generator
│   │   └── templates/
│   │       ├── report.html     ← Zwart/wit rapport template
│   │       └── executive.html  ← Compacte management samenvatting
│   ├── scraper/
│   │   ├── cve_scraper.py
│   │   ├── technique_scraper.py
│   │   ├── exploit_scraper.py  ← NIEUW
│   │   └── scheduler.py
│   └── exploit_correlator.py   ← NIEUW
│
└── data/
    └── scans/                  ← Lokale scanresultaten
```

**Communicatie:** Tauri frontend ↔ Python FastAPI via `localhost:7823` (of Tauri sidecar).
**Tauri sidecar:** Start Python FastAPI automatisch als de desktop app opent. Stopt als de app sluit.

---

## TAAK 1 — TAURI DESKTOP APP SETUP

### 1a. Tauri configuratie (`src-tauri/tauri.conf.json`)

```json
{
  "package": {
    "productName": "CyberPulse",
    "version": "0.1.0"
  },
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devPath": "http://localhost:5173",
    "distDir": "../frontend/dist"
  },
  "tauri": {
    "windows": [
      {
        "title": "CyberPulse",
        "width": 1280,
        "height": 800,
        "minWidth": 1024,
        "minHeight": 600,
        "resizable": true,
        "fullscreen": false,
        "decorations": true,
        "transparent": false,
        "theme": "Dark"
      }
    ],
    "bundle": {
      "identifier": "nl.d-esign.cyberpulse",
      "icon": ["icons/icon.png", "icons/icon.ico", "icons/icon.icns"]
    },
    "allowlist": {
      "all": false,
      "shell": { "execute": true, "sidecar": true },
      "path": { "all": true },
      "fs": { "all": true, "scope": ["$APPDATA/cyberpulse/**", "$DOCUMENT/**"] },
      "dialog": { "open": true, "save": true }
    },
    "security": {
      "csp": "default-src 'self'; connect-src http://localhost:7823"
    }
  }
}
```

### 1b. Python sidecar (`src-tauri/src/main.rs`)

```rust
// Start Python FastAPI als sidecar bij app launch
// Stop sidecar netjes bij app close (prevent orphan processes)

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Start Python backend als sidecar
            let sidecar = app.shell().sidecar("cyberpulse-engine")
                .expect("Python sidecar niet gevonden");
            
            let (mut rx, child) = sidecar.spawn()
                .expect("Kon Python backend niet starten");
            
            // Bewaar child handle zodat we hem kunnen stoppen
            app.manage(std::sync::Mutex::new(Some(child)));
            
            Ok(())
        })
        .on_window_event(|event| {
            // Stop Python backend als venster sluit
            if let tauri::WindowEvent::Destroyed = event.event() {
                // kill sidecar
            }
        })
        .run(tauri::generate_context!())
        .expect("error starting CyberPulse");
}
```

### 1c. Startup health check

Bij opstarten:
1. Tauri start Python sidecar
2. Frontend poll `GET /health` elke 500ms tot 200 response
3. Toon loading screen: `"CyberPulse start..."` met simpele progress bar
4. Na success: toon Dashboard
5. Bij fout na 10s: toon foutmelding met "Herstart" knop

---

## TAAK 2 — UI DESIGN SYSTEM (ZWART/WIT — STRIKT)

### Designprincipes

- **Puur zwart en wit.** Geen blauw, groen, paars. Nul kleur behalve voor severity badges.
- **Monospace typografie** voor alle technische output, scannamen, module IDs.
- **Proportionele typografie** voor leesbare tekst en beschrijvingen.
- **Brutaal minimalistisch** — geen afgeronde hoeken op containers, geen schaduwen, geen gradients.
- **1px borders** overal. Geen dikke lijnen.
- **Veel witruimte** (of zwarte ruimte) — ademruimte is functionaliteit.

### CSS Design System (`frontend/src/styles/global.css`)

```css
/* ── TOKENS ─────────────────────────────── */
:root {
  --bg:         #0a0a0a;   /* bijna-zwart achtergrond */
  --bg-2:       #111111;   /* sidebar, cards */
  --bg-3:       #1a1a1a;   /* hover states, inputs */
  --border:     #2a2a2a;   /* subtiele borders */
  --border-2:   #3a3a3a;   /* actieve borders */
  --text:       #f0f0f0;   /* primaire tekst */
  --text-2:     #888888;   /* secundaire tekst, labels */
  --text-3:     #555555;   /* placeholder, disabled */
  --accent:     #ffffff;   /* enige accent kleur = wit */
  
  /* Severity — ENIGE toegestane kleuren */
  --critical:   #ff3333;
  --high:       #ff8800;
  --medium:     #ffcc00;
  --low:        #888888;
  --info:       #444444;
  
  /* Type */
  --font-ui:    'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  --font-read:  'Inter', 'Helvetica Neue', system-ui, sans-serif;
  
  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 16px;
  --space-4: 24px;
  --space-5: 32px;
  --space-6: 48px;
  
  /* Geen border-radius voor containers */
  --radius: 0px;
  --radius-sm: 2px;  /* alleen voor badges/pills */
}

/* ── RESET ───────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 13px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* ── LAYOUT ──────────────────────────────── */
.app-shell {
  display: grid;
  grid-template-columns: 220px 1fr;
  grid-template-rows: 1fr;
  height: 100vh;
}

/* ── SIDEBAR ─────────────────────────────── */
.sidebar {
  background: var(--bg-2);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: var(--space-4) 0;
  overflow-y: auto;
}
.sidebar-logo {
  padding: 0 var(--space-4) var(--space-5);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: var(--accent);
  text-transform: uppercase;
}
.sidebar-logo span { color: var(--text-2); font-weight: 400; }
.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  color: var(--text-2);
  cursor: pointer;
  transition: color 0.1s, background 0.1s;
  border-left: 2px solid transparent;
  font-size: 12px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.nav-item:hover { color: var(--text); background: var(--bg-3); }
.nav-item.active { color: var(--accent); border-left-color: var(--accent); background: var(--bg-3); }

/* ── MAIN CONTENT ────────────────────────── */
.main {
  overflow-y: auto;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.page-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  padding-bottom: var(--space-3);
}
.page-title { font-size: 18px; font-weight: 700; letter-spacing: 0.05em; }
.page-meta { font-size: 11px; color: var(--text-2); }

/* ── CARDS ───────────────────────────────── */
.card {
  background: var(--bg-2);
  border: 1px solid var(--border);
  padding: var(--space-4);
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border);
}
.card-title { font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-2); }

/* ── BUTTONS ─────────────────────────────── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-2);
  background: transparent;
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 12px;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: background 0.1s, border-color 0.1s;
  text-transform: uppercase;
}
.btn:hover { background: var(--bg-3); border-color: var(--text-2); }
.btn-primary { background: var(--accent); color: var(--bg); border-color: var(--accent); }
.btn-primary:hover { background: #cccccc; }
.btn-danger { border-color: var(--critical); color: var(--critical); }

/* ── INPUTS ──────────────────────────────── */
input, select, textarea {
  background: var(--bg-3);
  border: 1px solid var(--border);
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 13px;
  padding: var(--space-2) var(--space-3);
  width: 100%;
  outline: none;
  transition: border-color 0.1s;
}
input:focus, select:focus { border-color: var(--border-2); }
label {
  display: block;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-2);
  margin-bottom: var(--space-1);
}

/* ── SEVERITY BADGES ─────────────────────── */
.badge {
  display: inline-block;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border-radius: var(--radius-sm);
}
.badge-critical { background: var(--critical); color: #fff; }
.badge-high     { background: var(--high); color: #000; }
.badge-medium   { background: var(--medium); color: #000; }
.badge-low      { background: transparent; border: 1px solid var(--low); color: var(--low); }
.badge-info     { background: transparent; border: 1px solid var(--info); color: var(--text-3); }

/* ── RISK SCORE DISPLAY ──────────────────── */
.risk-score {
  font-size: 72px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
}
.risk-score.critical { color: var(--critical); }
.risk-score.high     { color: var(--high); }
.risk-score.medium   { color: var(--medium); }
.risk-score.low      { color: var(--text-2); }

/* ── TERMINAL / LOG OUTPUT ───────────────── */
.terminal {
  background: #000;
  border: 1px solid var(--border);
  padding: var(--space-3);
  font-family: var(--font-ui);
  font-size: 12px;
  line-height: 1.8;
  overflow-y: auto;
  max-height: 400px;
  color: #cccccc;
}
.terminal .log-module  { color: #ffffff; font-weight: 700; }
.terminal .log-finding { color: var(--high); }
.terminal .log-error   { color: var(--critical); }
.terminal .log-done    { color: var(--text-2); }
.terminal .log-info    { color: var(--text-3); }

/* ── PROGRESS BAR ────────────────────────── */
.progress-track { height: 2px; background: var(--border); width: 100%; }
.progress-fill  { height: 100%; background: var(--accent); transition: width 0.3s; }

/* ── FINDINGS TABLE ──────────────────────── */
.findings-table { width: 100%; border-collapse: collapse; }
.findings-table th {
  text-align: left;
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-3);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border);
  font-weight: 400;
}
.findings-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border);
  vertical-align: top;
  font-size: 12px;
}
.findings-table tr:hover td { background: var(--bg-3); }
.finding-title { font-weight: 700; color: var(--text); }
.finding-desc  { color: var(--text-2); font-size: 11px; margin-top: 2px; }

/* ── MODULE PROGRESS GRID ────────────────── */
.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 1px;
  background: var(--border);
}
.module-cell {
  background: var(--bg-2);
  padding: var(--space-2) var(--space-3);
  font-size: 11px;
}
.module-cell.running { background: var(--bg-3); color: var(--accent); }
.module-cell.done    { color: var(--text-3); }
.module-cell.error   { color: var(--critical); }
.module-cell.queued  { color: var(--text-3); opacity: 0.4; }
```

---

## TAAK 3 — PAGINA'S & COMPONENTEN

### 3a. Dashboard (`Dashboard.svelte`)

Layout:
```
┌─────────────────────────────────────────────┐
│ CYBERPULSE                    [+ Nieuwe scan]│
├─────────────────────────────────────────────┤
│ RECENTE SCANS                               │
│                                             │
│ TARGET          TYPE    SCORE  DATUM  STATUS│
│ ─────────────────────────────────────────  │
│ example.nl      Full     78    15mrt  Klaar │
│ 192.168.1.1     Quick    23    14mrt  Klaar │
│ myapp.local     Mobile   91    13mrt  Klaar │
│                                             │
│ [Meer laden]                                │
└─────────────────────────────────────────────┘
```

- Klikken op een scan → gaat naar Report pagina
- `+ Nieuwe scan` knop → gaat naar NewScan pagina
- Score wordt weergegeven als getal + kleur (critical/high/medium/low)

### 3b. Nieuwe Scan (`NewScan.svelte`)

```
┌─────────────────────────────────────────────┐
│ NIEUWE SCAN                                 │
├─────────────────────────────────────────────┤
│ TARGET                                      │
│ [                                          ]│
│  Vul in: URL, IP, domein, APK-pad, .ipa-pad│
│                                             │
│ TARGET TYPE              SCAN TYPE          │
│ ○ Website/Webapp         ○ Snel (8 modules) │
│ ○ REST API               ○ Standaard (50)   │
│ ○ Dashboard/SPA          ○ Volledig (100)   │
│ ○ Mobile iOS (.ipa)      ○ Aangepast        │
│ ○ Mobile Android (.apk)                     │
│ ○ Desktop app                               │
│ ○ Netwerk/IP range                          │
│                                             │
│ MODUS                                       │
│ ○ Blackbox   ○ Graybox   ○ Whitebox         │
│                                             │
│ [Credentials invullen — alleen bij Graybox/White]│
│                                             │
│           [SCAN STARTEN]                    │
└─────────────────────────────────────────────┘
```

### 3c. Scan Progress (`ScanProgress.svelte`)

```
┌─────────────────────────────────────────────┐
│ SCAN — example.nl                   [STOP] │
├───────────────────────────────────────────  │
│ Voortgang ████████████░░░░░░░░ 14/50        │
│                                             │
│ MODULE GRID:                                │
│ [01✓][02✓][03✓][04✓][05►][06·][07·][08·]  │
│ [09·][10·][11·][12·]...                     │
│                                             │
│ BEVINDINGEN (live):                         │
│ [HIGH]  Open redirect gevonden in /redirect │
│ [CRIT]  SQL injection op /api/login         │
│ [MED]   TLS 1.0 nog actief                  │
│                                             │
│ TERMINAL:                                   │
│ ┌───────────────────────────────────────┐   │
│ │ [05] Injection Testing — gestart      │   │
│ │ → sqlmap: testing /api/login...       │   │
│ │ → FOUND: parameter 'id' injectable    │   │
│ │ [04] Web Vulnerabilities — klaar (3s) │   │
│ └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 3d. Rapport (`Report.svelte`)

```
┌─────────────────────────────────────────────┐
│ RAPPORT — example.nl        [PDF] [Opnieuw] │
├─────────────────────────────────────────────┤
│                                             │
│     78                                      │
│  HOOG RISICO                                │
│  15 maart 2026 — Volledig — 47 minuten     │
│                                             │
│ SAMENVATTING ──────────────────────────────│
│  [AI-gegenereerde managementtekst]          │
│                                             │
│ BEVINDINGEN ───────────────────────────────│
│ ERNST   NAAM                   MODULE       │
│ ──────  ─────────────────────  ──────────  │
│ CRIT    SQL injection login    m05          │
│ HIGH    Open redirect          m57          │
│ MED     TLS 1.0 actief         m94          │
│ LOW     X-Frame-Options mist   m11          │
│                                             │
│ AANBEVELINGEN ─────────────────────────────│
│  1. Patch SQL injection — hoog risico       │
│  2. Upgrade TLS naar 1.3                    │
│  3. ...                                     │
└─────────────────────────────────────────────┘
```

### 3e. Instellingen (`Settings.svelte`)

```
┌─────────────────────────────────────────────┐
│ INSTELLINGEN                                │
├─────────────────────────────────────────────┤
│ AI / API                                    │
│  DeepSeek API Key  [●●●●●●●●●●●●●●●●●●●●] │
│  Model             [deepseek-chat        ▾] │
│  Temperature       [0.3                    ]│
│                                             │
│ SCANNER                                     │
│  Nmap timing       [T4                    ▾]│
│  Max threads       [50                     ]│
│  Scan timeout (s)  [300                    ]│
│  Wordlist pad      [/usr/share/wordlists/  ]│
│                                             │
│ EXTERNE API KEYS (optioneel)                │
│  Shodan            [                       ]│
│  AbuseIPDB         [                       ]│
│  VirusTotal        [                       ]│
│  HIBP              [                       ]│
│                                             │
│ TOOLS CHECK                                 │
│  nmap      ✓   nuclei    ✓   gobuster ✓    │
│  sqlmap    ✓   testssl   ✓   whatweb  ✓    │
│  gitleaks  ✗   ffuf      ✓   ferox    ✓    │
│                                             │
│           [Opslaan]                         │
└─────────────────────────────────────────────┘
```

---

## TAAK 4 — PDF RAPPORT TEMPLATE (ZWART/WIT)

**Bestand:** `engine/reports/templates/report.html`

Volledig nieuw ontwerp. Regels:
- Zwarte tekst op witte achtergrond (print-vriendelijk)
- Geen kleuren behalve severity badges
- Monospace font voor technische details, serif voor leestekst
- Geen logo's, geen marketing
- Strak rastergebaseerd layout

```html
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Crimson+Pro:wght@400;600&display=swap');

  :root {
    --black: #000000;
    --white: #ffffff;
    --gray-1: #111111;
    --gray-2: #333333;
    --gray-3: #666666;
    --gray-4: #999999;
    --gray-5: #cccccc;
    --gray-6: #eeeeee;
    --critical: #cc0000;
    --high:     #cc6600;
    --medium:   #999900;
    --low:      #666666;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  
  body {
    font-family: 'Crimson Pro', Georgia, serif;
    font-size: 11pt;
    color: var(--black);
    background: var(--white);
    line-height: 1.6;
  }

  /* ── COVERPAGE ── */
  .cover {
    height: 297mm;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 40mm 30mm;
    border-bottom: 3px solid var(--black);
    page-break-after: always;
  }
  .cover-brand {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10pt;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--gray-3);
  }
  .cover-target {
    font-family: 'JetBrains Mono', monospace;
    font-size: 32pt;
    font-weight: 700;
    line-height: 1.1;
    word-break: break-all;
  }
  .cover-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9pt;
    color: var(--gray-3);
    line-height: 2;
  }
  .cover-score {
    display: flex;
    align-items: baseline;
    gap: 16px;
    margin-top: 24px;
  }
  .score-number {
    font-family: 'JetBrains Mono', monospace;
    font-size: 96pt;
    font-weight: 700;
    line-height: 1;
  }
  .score-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12pt;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .score-number.critical { color: var(--critical); }
  .score-number.high     { color: var(--high); }
  .score-number.medium   { color: var(--medium); }
  .score-number.low      { color: var(--gray-3); }

  /* ── PAGINA LAYOUT ── */
  @page {
    size: A4;
    margin: 20mm 25mm;
    @bottom-left  { content: "CYBERPULSE — VERTROUWELIJK"; font-family: 'JetBrains Mono', monospace; font-size: 8pt; color: #999; }
    @bottom-right { content: "Pagina " counter(page); font-family: 'JetBrains Mono', monospace; font-size: 8pt; color: #999; }
  }

  /* ── SECTIES ── */
  .section { margin-bottom: 20mm; page-break-inside: avoid; }
  .section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8pt;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--gray-3);
    border-top: 1px solid var(--black);
    padding-top: 4px;
    margin-bottom: 8px;
  }
  .section-title {
    font-size: 16pt;
    font-weight: 600;
    margin-bottom: 8px;
  }

  /* ── BEVINDINGEN TABEL ── */
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  th {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8pt;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    text-align: left;
    padding: 6px 8px;
    border-bottom: 2px solid var(--black);
    font-weight: 700;
  }
  td {
    font-size: 10pt;
    padding: 8px;
    border-bottom: 1px solid var(--gray-5);
    vertical-align: top;
  }
  tr:last-child td { border-bottom: none; }

  /* ── SEVERITY BADGES ── */
  .sev {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 0.05em;
    padding: 2px 5px;
    text-transform: uppercase;
    display: inline-block;
  }
  .sev-critical { border: 1.5px solid var(--critical); color: var(--critical); }
  .sev-high     { border: 1.5px solid var(--high); color: var(--high); }
  .sev-medium   { border: 1.5px solid var(--medium); color: var(--medium); }
  .sev-low      { border: 1.5px solid var(--gray-4); color: var(--gray-4); }
  .sev-info     { border: 1.5px solid var(--gray-5); color: var(--gray-5); }

  /* ── FINDING DETAIL BLOCK ── */
  .finding-block {
    border: 1px solid var(--gray-5);
    padding: 12px;
    margin-bottom: 8px;
    page-break-inside: avoid;
  }
  .finding-block-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--gray-6);
    padding-bottom: 8px;
  }
  .finding-name { font-size: 12pt; font-weight: 600; }
  .finding-section { margin-top: 8px; }
  .finding-section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8pt;
    color: var(--gray-3);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }

  /* ── CODE BLOCKS ── */
  code, pre {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9pt;
    background: var(--gray-6);
    padding: 2px 4px;
  }
  pre { padding: 8px; display: block; overflow-x: auto; }

  /* ── AANBEVELINGEN ── */
  .rec { display: flex; gap: 12px; margin-bottom: 12px; }
  .rec-number {
    font-family: 'JetBrains Mono', monospace;
    font-size: 24pt;
    font-weight: 700;
    color: var(--gray-5);
    line-height: 1;
    min-width: 40px;
  }
  .rec-content { flex: 1; }
  .rec-actie { font-size: 12pt; font-weight: 600; margin-bottom: 4px; }
  .rec-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8pt;
    color: var(--gray-3);
  }
</style>
</head>
<body>

<!-- COVER -->
<div class="cover">
  <div class="cover-brand">CyberPulse — Penetratietestrapport — Vertrouwelijk</div>
  <div>
    <div class="cover-target">{{ target }}</div>
    <div class="cover-score">
      <div class="score-number {{ risk_class }}">{{ risicoscore }}</div>
      <div>
        <div class="score-label">{{ niveau }}</div>
        <div style="font-family: 'JetBrains Mono'; font-size: 9pt; color: #999; margin-top: 4px;">Risicoscore / 100</div>
      </div>
    </div>
  </div>
  <div class="cover-meta">
    Gegenereerd op: {{ generated_at }}<br>
    Scantype: {{ scan_type }}<br>
    Modules uitgevoerd: {{ modules_count }}<br>
    Bevindingen: {{ findings_count }} ({{ critical_count }} kritiek, {{ high_count }} hoog)
  </div>
</div>

<!-- MANAGEMENT SAMENVATTING -->
<div class="section">
  <div class="section-label">01 — Managementsamenvatting</div>
  <p style="font-size: 12pt; line-height: 1.8;">{{ management_samenvatting }}</p>
</div>

<!-- BEVINDINGEN OVERZICHT -->
<div class="section">
  <div class="section-label">02 — Bevindingen overzicht</div>
  <table>
    <thead>
      <tr><th>Ernst</th><th>Bevinding</th><th>Module</th><th>CVE</th></tr>
    </thead>
    <tbody>
      {% for f in bevindingen %}
      <tr>
        <td><span class="sev sev-{{ f.ernst }}">{{ f.ernst }}</span></td>
        <td>{{ f.titel }}</td>
        <td style="font-family: 'JetBrains Mono'; font-size: 9pt; color: #666;">{{ f.module }}</td>
        <td style="font-family: 'JetBrains Mono'; font-size: 9pt; color: #666;">{{ f.cve or '—' }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<!-- BEVINDINGEN DETAIL -->
<div class="section">
  <div class="section-label">03 — Bevindingen detail</div>
  {% for f in bevindingen %}
  <div class="finding-block">
    <div class="finding-block-header">
      <div class="finding-name">{{ f.titel }}</div>
      <span class="sev sev-{{ f.ernst }}">{{ f.ernst }}</span>
    </div>
    <div class="finding-section">
      <div class="finding-section-label">Beschrijving</div>
      <p>{{ f.beschrijving }}</p>
    </div>
    <div class="finding-section">
      <div class="finding-section-label">Impact</div>
      <p>{{ f.impact }}</p>
    </div>
    <div class="finding-section">
      <div class="finding-section-label">Aanbeveling</div>
      <p>{{ f.aanbeveling }}</p>
    </div>
    {% if f.referenties %}
    <div class="finding-section">
      <div class="finding-section-label">Referenties</div>
      <p style="font-family: 'JetBrains Mono'; font-size: 9pt;">{{ f.referenties | join(' · ') }}</p>
    </div>
    {% endif %}
  </div>
  {% endfor %}
</div>

<!-- AANBEVELINGEN -->
<div class="section">
  <div class="section-label">04 — Prioriteiten</div>
  {% for r in aanbevelingen_prioriteit %}
  <div class="rec">
    <div class="rec-number">{{ r.prioriteit }}</div>
    <div class="rec-content">
      <div class="rec-actie">{{ r.actie }}</div>
      <div style="margin: 4px 0 6px; font-size: 10pt; color: #333;">{{ r.reden }}</div>
      <div class="rec-meta">Complexiteit: {{ r.complexiteit }}</div>
    </div>
  </div>
  {% endfor %}
</div>

<!-- TECHNISCHE DETAILS -->
<div class="section">
  <div class="section-label">05 — Technische details</div>
  <pre>{{ technische_details }}</pre>
</div>

</body>
</html>
```

---

## TAAK 5 — NIEUWE SCANMODULES (m91–m100)

Elke module volgt dit patroon — **niet afwijken**:

```python
import subprocess, shutil, json, os
from pathlib import Path

class Scanner:
    name = "Module Naam"
    phase = "reconnaissance"  # reconnaissance|scanning|exploitation|post|reporting
    description = "Korte beschrijving van wat deze module doet"
    target_types = ["web", "api", "network"]  # zie target types hieronder

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 300)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def run(self) -> dict:
        if not self._tool_available("toolnaam"):
            return {"findings": [], "raw_output": "toolnaam niet gevonden in PATH", "error": None}
        try:
            # ... uitvoering
            return {"findings": [...], "raw_output": "...", "error": None}
        except Exception as e:
            return {"findings": [], "raw_output": "", "error": str(e)}
```

### Target Types (nieuw veld op elke module)

```python
TARGET_TYPES = [
    "web",       # websites, webapps, SPA's, dashboards
    "api",       # REST API, GraphQL, WebSocket endpoints
    "mobile",    # iOS .ipa, Android .apk bestanden
    "desktop",   # desktop applicaties (binary, installer)
    "network",   # IP-adressen, IP-ranges, netwerken
    "all",       # werkt op alles
]
```

De `module_runner.py` filtert automatisch modules op `target_type` zodat mobiele modules niet draaien bij een netwerkscan.

---

### m91.py — Nuclei Template Scanner
```
phase: scanning
target_types: ["web", "api"]
tool: nuclei
commando: nuclei -u {target} -severity critical,high,medium -json -o {output} -silent -timeout 30
parsing: elke JSON-regel = één bevinding, map severity direct
snelle scan: JA (alleen critical+high, timeout 20s)
```

### m92.py — Gobuster Directory Fuzzing
```
phase: scanning
target_types: ["web", "api"]
tool: gobuster (fallback: ffuf)
wordlist: zoek in volgorde: config path, /usr/share/wordlists/dirb/common.txt, SecLists
commando: gobuster dir -u {target} -w {wordlist} -o {output} -q --no-error -t 30
findings: 200/201 = info, pad bevat "admin|backup|config|secret|.env|.git" = medium/high
```

### m93.py — SQLmap Injection
```
phase: exploitation
target_types: ["web", "api"]
tool: sqlmap
commando: sqlmap -u {target} --batch --random-agent --level=2 --risk=1 --forms --crawl=2 --threads=3 --timeout=30 --no-cast
findings: elke "injection point" = critical bevinding met parameter naam en type
```

### m94.py — Testssl.sh TLS Audit
```
phase: scanning
target_types: ["web", "api", "network"]
tool: testssl.sh
check: alleen als HTTPS actief is (poort 443 open)
commando: testssl.sh --jsonfile={output} --severity HIGH --quiet {target}
findings: map severity direct, filter INFO eruit
```

### m95.py — Feroxbuster Recursieve Scan
```
phase: scanning
target_types: ["web"]
tool: feroxbuster
commando: feroxbuster -u {target} -w {wordlist} --json -o {output} --depth 3 --silent --auto-tune --timeout 10 --threads 30
findings: zelfde logica als m92, maar recursief
```

### m96.py — Nmap NSE Scripts
```
phase: scanning
target_types: ["web", "network", "api"]
tool: nmap
commando: nmap -sV --script=vuln,auth,default --script-args=unsafe=0 -oJ {output} --open -T3 {target}
findings: "VULNERABLE" in output = high/critical afhankelijk van script naam
```

### m97.py — WhatWeb Fingerprinting
```
phase: reconnaissance
target_types: ["web"]
tool: whatweb
commando: whatweb -a 3 --log-json={output} --quiet {target}
findings: verouderde versies = medium, EoL software = high
sla op: technologie-inventaris als JSON voor gebruik door andere modules
```

### m98.py — Gitleaks & Secrets Scan
```
phase: reconnaissance
target_types: ["web", "api", "all"]
tool: gitleaks (optioneel) + ingebouwde regex scan
web scan: download homepage + linked JS, zoek op secrets patterns
findings: elke match = critical, REDACT waarde in output (toon eerste 4 + *** + laatste 4)
patterns: AWS keys, Stripe keys, private keys, DB URLs, JWT secrets, SendGrid, generic API keys
```

### m98b.py — Mobile Android Scan (.apk)
```
phase: scanning
target_types: ["mobile"]
tool: apktool, jadx (optioneel), grep
stappen:
  1. apktool d {apk_path} -o {output}/apk_decoded --no-res
  2. Zoek in gedecompileerde code op: hardcoded URLs, API keys, secrets, HTTP (niet HTTPS)
  3. Analyseer AndroidManifest.xml: permissions, exported components, backup=true
  4. Zoek op debuggable=true in manifest
findings:
  - debuggable=true → high
  - backup=true → medium
  - hardcoded secrets → critical
  - cleartext HTTP → medium
  - gevaarlijke permissions (READ_CONTACTS, SEND_SMS) → info/medium
```

### m98c.py — Mobile iOS Scan (.ipa)
```
phase: scanning
target_types: ["mobile"]
tool: unzip, grep, strings
stappen:
  1. unzip {ipa_path} -d {output}/ipa_extracted
  2. Zoek Mach-O binaries in Payload/*.app/
  3. strings op binary: zoek API keys, URLs, secrets
  4. Analyseer Info.plist: NSAllowsArbitraryLoads, permissions
  5. Controleer op ATS (App Transport Security) uitzonderingen
findings:
  - NSAllowsArbitraryLoads = true → high
  - ATS uitzonderingen per domein → medium
  - Hardcoded secrets in binary → critical
  - Debuggable binary → medium
```

### m99.py — Metasploit Auxiliaries
```
phase: scanning
target_types: ["web", "network", "api"]
tool: msfconsole
STRICT: alleen auxiliary/scanner/* en auxiliary/gather/* — NOOIT exploit/*
interface: resource script via msfconsole -q -r
modules: http_version, smb_version, ssl heartbleed, ftp_anon
parsing: zoek "vulnerable", "version detected" in output
```

### m100.py — Shodan Passieve Intelligence
```
phase: reconnaissance
target_types: ["web", "network", "api"]
service: Shodan API
vereist: SHODAN_API_KEY in .env, anders skip met info-bericht
data: open poorten, CVEs, certificaten, historische data, tags
findings: CVE CVSS ≥ 7.0 → high, onverwachte poorten → medium
```

### m101.py — Desktop App Analyse
```
phase: scanning
target_types: ["desktop"]
tool: strings, file, ldd (Linux), depends (Windows via wine)
stappen:
  1. file {binary} → detecteer type (ELF/PE/Mach-O)
  2. strings {binary} | grep -E "(http|api|key|token|secret|password)" → hardcoded data
  3. ldd {binary} → verouderde dynamische libraries
  4. Controleer of binary gestrip is (geen debug symbols = moeilijker te analyseren maar normaal voor productie)
findings:
  - Hardcoded URLs/keys → critical/high
  - Verouderde libraries met bekende CVEs → high/medium
  - Unencrypted HTTP endpoints → medium
```

---

## TAAK 6 — EXPLOIT CORRELATOR

**Bestand:** `engine/exploit_correlator.py`

```python
class ExploitCorrelator:
    """
    Verrijkt bevindingen met exploit-beschikbaarheid en CVSS scores.
    Gebruikt lokale cache — geen API calls tijdens scan tenzij cache leeg.
    """
    
    def correlate(self, findings: list[dict]) -> list[dict]:
        for finding in findings:
            for ref in finding.get("referenties", []):
                if ref.startswith("CVE-"):
                    finding["cvss_score"] = self.get_cvss(ref)
                    finding["kev_listed"] = self.check_kev(ref)
                    finding["exploitdb"] = self.search_exploitdb(ref)
                    finding["exploit_available"] = bool(finding["exploitdb"])
        return findings
    
    def search_exploitdb(self, cve: str) -> list[dict]:
        # searchsploit {cve} --json 2>/dev/null
        result = subprocess.run(["searchsploit", cve, "--json"], capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout or '{"RESULTS_EXPLOIT": []}')
        return data.get("RESULTS_EXPLOIT", [])
    
    def check_kev(self, cve: str) -> bool:
        kev_path = Path("data/kev_cache.json")
        if not kev_path.exists():
            return False
        kev = json.loads(kev_path.read_text())
        return any(v["cveID"] == cve for v in kev.get("vulnerabilities", []))
    
    def get_cvss(self, cve: str) -> float | None:
        # Check lokale SQLite cache eerst
        # Fallback: NVD API met rate-limit
        ...
```

Integreer in `scanner.py`: roep correlator aan **vóór** AI-analyse zodat DeepSeek ook exploit-context heeft.

---

## TAAK 7 — LANDING PAGE VERWIJDEREN

**Actie:** Verwijder of deactiveer de landing/marketing pagina volledig.

```python
# In engine/web/app.py (als dit nog bestaat als FastAPI app):
# Verwijder route: GET /
# Verwijder route: GET /landing

# De app opent direct op: Dashboard
# Geen welkomstscherm, geen marketing, geen uitleg
# Eerste scherm = lijst van recente scans + [Nieuwe scan] knop
```

Als er een `landing.html` template is: verwijder het bestand.
Als er een Next.js landing page is (`/app/page.tsx` of `/app/(marketing)/`): verwijder de marketing route, redirect `/` direct naar `/dashboard`.

---

## TAAK 8 — SCOPE VALIDATOR

**Bestand:** `engine/scope_validator.py`

```python
class ScopeValidator:
    ALWAYS_BLOCKED = [
        "169.254.169.254",  # AWS/Azure metadata
        "169.254.170.2",    # ECS metadata
        "100.100.100.200",  # Alibaba metadata
    ]
    
    def validate(self, requested_host: str, declared_target: str) -> bool:
        """Retourneert True als request binnen scope valt"""
        ...
    
    def is_subdomain(self, host: str, target: str) -> bool:
        """example.nl → sub.example.nl is toegestaan"""
        ...
    
    def log_violation(self, module: str, requested: str, declared: str):
        """Logt scope violations naar data/scope_violations.log"""
        ...
```

Injecteer in `module_runner.py`: elke subprocess-aanroep passeert de scope validator.

---

## BESTANDSSTRUCTUUR NA ALLE WIJZIGINGEN

```
cyberpulse/
├── src-tauri/
│   ├── src/main.rs
│   ├── tauri.conf.json
│   └── Cargo.toml
│
├── frontend/
│   ├── src/
│   │   ├── App.svelte
│   │   ├── routes/
│   │   │   ├── Dashboard.svelte
│   │   │   ├── NewScan.svelte
│   │   │   ├── ScanProgress.svelte
│   │   │   ├── Report.svelte
│   │   │   └── Settings.svelte
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── stores.ts
│   │   └── styles/global.css     ← Volledig nieuw zwart/wit systeem
│   └── package.json
│
├── engine/
│   ├── main.py                   ← FastAPI app (geen landing route meer)
│   ├── config.py
│   ├── scanner.py                ← Uitgebreid met target_type + scope check
│   ├── module_runner.py          ← Uitgebreid met target_type filtering
│   ├── scope_validator.py        ← NIEUW
│   ├── exploit_correlator.py     ← NIEUW
│   ├── modules/
│   │   ├── m01.py … m90.py       ← Bestaand (voeg target_types toe)
│   │   ├── m91.py                ← NIEUW: Nuclei
│   │   ├── m92.py                ← NIEUW: Gobuster
│   │   ├── m93.py                ← NIEUW: SQLmap
│   │   ├── m94.py                ← NIEUW: Testssl
│   │   ├── m95.py                ← NIEUW: Feroxbuster
│   │   ├── m96.py                ← NIEUW: Nmap NSE
│   │   ├── m97.py                ← NIEUW: WhatWeb
│   │   ├── m98.py                ← NIEUW: Gitleaks/Secrets
│   │   ├── m98b.py               ← NIEUW: Android APK
│   │   ├── m98c.py               ← NIEUW: iOS IPA
│   │   ├── m99.py                ← NIEUW: Metasploit aux
│   │   ├── m100.py               ← NIEUW: Shodan
│   │   └── m101.py               ← NIEUW: Desktop binary
│   ├── ai/
│   │   ├── analyzer.py           ← ONGEWIJZIGD (DeepSeek)
│   │   ├── formatter.py
│   │   └── prompts.py
│   ├── reports/
│   │   ├── generator.py
│   │   └── templates/
│   │       ├── report.html       ← Volledig nieuw zwart/wit design
│   │       └── executive.html    ← NIEUW: compacte versie
│   └── scraper/
│       ├── cve_scraper.py
│       ├── technique_scraper.py
│       └── exploit_scraper.py    ← NIEUW: ExploitDB sync
│
└── data/
    └── scans/
```

---

## IMPLEMENTATIE VOLGORDE

**Stap 1 — Fundament:**
1. Verwijder landing page en alle marketing routes
2. Nieuw CSS design system (global.css) — zwart/wit
3. Nieuw PDF rapport template
4. Tauri project initialiseren + Python sidecar

**Stap 2 — UI pagina's:**
5. Dashboard, NewScan, ScanProgress, Report, Settings componenten
6. Target type selector in NewScan
7. Tools-check in Settings

**Stap 3 — Nieuwe modules:**
8. m91 Nuclei + m92 Gobuster (grootste impact, simpelste implementatie)
9. m94 Testssl + m97 WhatWeb + m98 Gitleaks
10. m98b Android + m98c iOS + m101 Desktop
11. m93 SQLmap + m96 NSE + m99 Metasploit + m100 Shodan

**Stap 4 — Intelligence:**
12. Exploit correlator
13. Scope validator
14. Target type filtering in module runner

---

## RANDVOORWAARDEN

- **Framework:** Svelte (voorkeur) of React — in Tauri venster
- **Python:** 3.11+, FastAPI, uvicorn
- **Tauri:** v1.x of v2.x
- **Communicatie:** REST + SSE voor live output (bestaande SSE aanpak behouden)
- **Fonts:** JetBrains Mono (via Google Fonts of lokaal bundelen in Tauri)
- **Alle kleuren in de UI:** uitsluitend CSS variabelen — geen hardcoded hex buiten global.css
- **Geen externe analytics, geen telemetrie, geen tracking**
- **DeepSeek API key:** alleen in `.env`, nooit in frontend bundle

---

*CyberPulse — Closed Source — NDA — Persoonlijk gebruik tijdens testfase*
