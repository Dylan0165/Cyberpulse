"""AI prompt templates for DeepSeek analysis.

All prompts are in Dutch as specified. The system prompt instructs the model
to return structured JSON with severity ratings and recommendations.
"""

SYSTEM_PROMPT = """Je bent CyberPulse AI, een expert cybersecurity-analist gespecialiseerd in penetratietesten.
Je analyseert scanresultaten en geeft een professionele beoordeling in het Nederlands.

Je taak:
1. Analyseer alle scanresultaten grondig
2. Classificeer elke bevinding op ernst (critical, high, medium, low, info)
3. Geef concrete aanbevelingen om elk probleem op te lossen
4. Schrijf een samenvatting geschikt voor management (niet-technisch)
5. Schrijf een technisch gedeelte met alle details

Antwoord UITSLUITEND in valid JSON met exact dit schema:

{
    "samenvatting": {
        "risicoscore": 0-100,
        "niveau": "kritiek|hoog|gemiddeld|laag|veilig",
        "korte_beschrijving": "..."
    },
    "management_samenvatting": "... max 200 woorden, begrijpelijk voor niet-technici ...",
    "bevindingen": [
        {
            "titel": "...",
            "module": "...",
            "ernst": "critical|high|medium|low|info",
            "beschrijving": "...",
            "impact": "...",
            "aanbeveling": "...",
            "referenties": ["CVE-...", "OWASP-...", "https://..."]
        }
    ],
    "aanbevelingen_prioriteit": [
        {
            "prioriteit": 1,
            "actie": "...",
            "reden": "...",
            "complexiteit": "laag|gemiddeld|hoog"
        }
    ],
    "technische_details": "... gedetailleerde technische analyse ..."
}

Regels:
- Gebruik ALLEEN Nederlands
- Wees specifiek en concreet in aanbevelingen
- Verwijs naar CVE-nummers en OWASP-categorien waar relevant
- De risicoscore is 0 (veilig) tot 100 (kritiek)
- Sorteer bevindingen op ernst (critical eerst)
- Geef maximaal 20 bevindingen (de belangrijkste)
- Geef maximaal 10 geprioriteerde aanbevelingen
"""


def build_scan_prompt(scan_data: dict) -> str:
    """Build the user prompt containing scan results for analysis."""
    target = scan_data.get("target", "unknown")
    scan_type = scan_data.get("scan_type", "unknown")
    total_findings = scan_data.get("total_findings", 0)
    results = scan_data.get("results", [])

    lines = [
        f"Analyseer de volgende penetratietest-resultaten voor {target}.",
        f"Type scan: {scan_type}",
        f"Totaal bevindingen: {total_findings}",
        "",
        "=== SCANRESULTATEN ===",
        "",
    ]

    # Prioritise modules that actually found something; skip empty ones
    results_with_findings = [r for r in results if r.get("findings")]
    results_empty = [r for r in results if not r.get("findings")]

    # Summary line for empty modules (keeps prompt small)
    if results_empty:
        empty_names = ", ".join(r.get("name", r.get("module_id", "?")) for r in results_empty[:30])
        lines.append(f"Modules zonder bevindingen ({len(results_empty)}x): {empty_names}")
        lines.append("")

    for result in results_with_findings:
        module_id = result.get("module_id", "?")
        name = result.get("name", "Unknown")
        success = result.get("success", False)
        findings = result.get("findings", [])
        raw = result.get("raw_output", "")

        # Sort findings by severity, take top 10 critical/high first
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        findings_sorted = sorted(findings, key=lambda f: severity_order.get(f.get("severity", "info"), 5))
        top_findings = findings_sorted[:10]

        lines.append(f"--- Module {module_id}: {name} ({len(findings)} bevindingen) ---")
        lines.append(f"Status: {'OK' if success else 'FOUT'}")

        for f in top_findings:
            severity = f.get("severity", "info")
            ftype = f.get("type", "unknown")
            detail = f.get("detail", f.get("description", str(f)))
            lines.append(f"  [{severity.upper()}] {ftype}: {detail[:150]}")

        if len(findings) > 10:
            lines.append(f"  ... en {len(findings) - 10} meer bevindingen (zelfde module)")

        if raw:
            lines.append(f"  Samenvatting: {raw[:300]}")

        lines.append("")

    lines.append("=== EINDE SCANRESULTATEN ===")
    lines.append("")
    lines.append("Geef nu je volledige analyse in het gevraagde JSON-formaat.")

    return "\n".join(lines)


def build_streaming_prompt(scan_data: dict) -> list[dict]:
    """Build the full message list for DeepSeek API call."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_scan_prompt(scan_data)},
    ]
