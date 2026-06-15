// Single source of truth for all user-facing Dutch terminology.
// Plain language: a non-technical business owner must understand every word.

// ── Scan types (scan_mode) ────────────────────────────────────────────────────
export const SCAN_TYPES: Record<string, { label: string; subtitle: string }> = {
  blackbox: {
    label: "Buitenstaander test",
    subtitle:
      "Wij weten niets over uw systeem vooraf — precies zoals een echte hacker te werk gaat. Meest realistisch.",
  },
  graybox: {
    label: "Gedeeltelijke test",
    subtitle:
      "Wij weten een beetje over uw systeem. De meest gebruikte test voor bedrijven.",
  },
  greybox: {
    label: "Gedeeltelijke test",
    subtitle:
      "Wij weten een beetje over uw systeem. De meest gebruikte test voor bedrijven.",
  },
  whitebox: {
    label: "Volledige doorlichting",
    subtitle:
      "Wij kennen uw systeem volledig. De meest grondige en complete test.",
  },
};

export function scanTypeLabel(mode?: string | null): string {
  if (!mode) return "Beveiligingstest";
  return SCAN_TYPES[mode.toLowerCase()]?.label ?? mode;
}

export function scanTypeSubtitle(mode?: string | null): string {
  if (!mode) return "";
  return SCAN_TYPES[mode.toLowerCase()]?.subtitle ?? "";
}

// ── Kali phases ───────────────────────────────────────────────────────────────
// Keyed by every variant used across the app (wizard + scan detail).
export const PHASES: Record<string, { label: string; desc: string }> = {
  recon: {
    label: "Verkenning",
    desc: "Wij brengen in kaart welke onderdelen van uw systeem zichtbaar zijn van buitenaf.",
  },
  vulnerability: {
    label: "Zwakke plekken zoeken",
    desc: "Wij controleren of er bekende beveiligingsproblemen aanwezig zijn.",
  },
  vuln_scan: {
    label: "Zwakke plekken zoeken",
    desc: "Wij controleren of er bekende beveiligingsproblemen aanwezig zijn.",
  },
  webapp: {
    label: "Website testen",
    desc: "Wij testen uw website op veelvoorkomende aanvalsmethoden.",
  },
  network: {
    label: "Netwerk controleren",
    desc: "Wij bekijken welke diensten bereikbaar zijn via het netwerk.",
  },
  auth: {
    label: "Wachtwoorden testen",
    desc: "Wij proberen in te loggen met veelgebruikte wachtwoorden om te zien of uw systeem beschermd is.",
  },
  ssl: {
    label: "Beveiligde verbinding checken",
    desc: "Wij controleren of uw internetverbinding goed beveiligd is.",
  },
  osint: {
    label: "Openbare informatie check",
    desc: "Wij zoeken naar informatie over uw bedrijf die onbedoeld openbaar is.",
  },
};

// ── Custom modules M09–M17 ────────────────────────────────────────────────────
export const MODULES: Record<string, { label: string; desc: string }> = {
  m09: {
    label: "Toegangspunten testen",
    desc: "Wij controleren of er gevoelige pagina's bereikbaar zijn die dat niet zouden mogen zijn.",
  },
  m10: {
    label: "Bekende lekken opzoeken",
    desc: "Wij zoeken uit of uw software bekende beveiligingslekken heeft.",
  },
  m11: {
    label: "Gevoelige bestanden checken",
    desc: "Wij controleren of er bestanden zichtbaar zijn die verborgen zouden moeten zijn.",
  },
  m12: {
    label: "Wachtwoordcheck",
    desc: "Wij testen of uw systeem beschermd is tegen veelgebruikte wachtwoorden.",
  },
  m13: {
    label: "Slimme vervolgtest",
    desc: "Onze AI bedenkt extra tests op basis van wat wij al gevonden hebben.",
  },
  m14: {
    label: "Vergelijking met vorige meting",
    desc: "Wij vergelijken deze scan met de vorige om te zien of het beter of slechter is geworden.",
  },
  m15: {
    label: "Aanvalssimulatie",
    desc: "Wij proberen kwetsbaarheden te combineren zoals een echte hacker dat zou doen.",
  },
  m16: {
    label: "Bewijs van risico",
    desc: "Wij bewijzen welke beveiligingsproblemen daadwerkelijk misbruikt kunnen worden.",
  },
  m17: {
    label: "Cloud beveiliging check",
    desc: "Wij controleren of uw cloudomgeving goed beveiligd is.",
  },
};

/** Dutch display name for any phase or module key (recon, ssl, m09, …). */
export function phaseLabel(key: string): string {
  const k = (key || "").toLowerCase();
  return PHASES[k]?.label ?? MODULES[k]?.label ?? key;
}

export function phaseDesc(key: string): string {
  const k = (key || "").toLowerCase();
  return PHASES[k]?.desc ?? MODULES[k]?.desc ?? "";
}

// ── Severity ──────────────────────────────────────────────────────────────────
export const SEVERITY: Record<string, { label: string; tooltip: string }> = {
  critical: {
    label: "Zeer ernstig",
    tooltip:
      "Moet zo snel mogelijk opgelost worden. Een aanvaller kan hier direct misbruik van maken.",
  },
  high: { label: "Ernstig", tooltip: "Los dit op binnen een week." },
  medium: { label: "Gemiddeld", tooltip: "Los dit op binnen een maand." },
  low: {
    label: "Laag risico",
    tooltip: "Aanbevolen om op te lossen maar geen directe dreiging.",
  },
  info: {
    label: "Informatie",
    tooltip: "Geen beveiligingsrisico, puur ter informatie.",
  },
};

export function severityLabel(sev?: string | null): string {
  return SEVERITY[(sev || "info").toLowerCase()]?.label ?? "Informatie";
}

export function severityTooltip(sev?: string | null): string {
  return SEVERITY[(sev || "info").toLowerCase()]?.tooltip ?? "";
}

// ── Scan status ───────────────────────────────────────────────────────────────
export const SCAN_STATUS: Record<string, string> = {
  completed: "Scan voltooid ✓",
  running: "Scan loopt...",
  analyzing: "Scan loopt...",
  pending: "In wachtrij",
  failed: "Scan mislukt",
  cancelled: "Scan geannuleerd",
  nda_required: "In wachtrij",
  verified: "In wachtrij",
};

export function statusLabel(status?: string | null): string {
  if (!status) return "Onbekend";
  return SCAN_STATUS[status.toLowerCase()] ?? status;
}

// ── Risk-score band (gauge value = risk, higher is worse) ─────────────────────
export function riskBand(score: number): { label: string; subtext: string } {
  if (score <= 30)
    return { label: "Goed beveiligd", subtext: "Uw systeem heeft weinig risico's" };
  if (score <= 60)
    return { label: "Verbetering nodig", subtext: "Er zijn aandachtspunten gevonden" };
  if (score <= 80)
    return { label: "Risico aanwezig", subtext: "Er zijn ernstige problemen gevonden" };
  return { label: "Dringend actie vereist", subtext: "Uw systeem loopt groot gevaar" };
}
