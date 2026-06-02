"""
CyberPulse Tool API — draait op de Kali VM (192.168.121.28:5001)

Ontvangt tool-opdrachten van de cyberpulse-web container,
voert de echte Kali-tools uit, en stuurt de output terug.

Start met:
    pip install flask
    python tool_api.py

Of als systemd service: zie kali/tool_api.service
"""

import json
import logging
import shlex
import shutil
import subprocess
import os
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("tool_api")

app = Flask(__name__)

# ── Veiligheidslijst: alleen deze tools mogen uitgevoerd worden ──────────────
ALLOWED_TOOLS = {
    "nmap", "nuclei", "sqlmap", "hydra", "gobuster", "nikto",
    "theharvester", "amass", "dnsrecon", "whatweb", "wfuzz",
    "dirb", "masscan", "ffuf", "feroxbuster", "wpscan",
    "netdiscover", "arpscan", "tcpdump", "tshark",
    "john", "hashcat", "hashid",
    "searchsploit", "msfconsole",
    "curl", "dig", "whois", "host",
}

# ── Maximum uitvoertijd per tool in seconden ──────────────────────────────────
TOOL_TIMEOUTS = {
    "nmap":        300,
    "nuclei":      600,
    "sqlmap":      600,
    "hydra":       300,
    "gobuster":    300,
    "nikto":       300,
    "theharvester":180,
    "amass":       600,
    "dnsrecon":    180,
    "wfuzz":       300,
    "ffuf":        300,
    "feroxbuster": 300,
    "masscan":     120,
    "default":     300,
}


def _is_safe_target(target: str) -> bool:
    """Minimale sanity-check: verwerp lege targets en shell-injectie-tekens."""
    if not target or len(target) > 253:
        return False
    bad_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]
    return not any(c in target for c in bad_chars)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "node": "kali-tool-api"})


@app.get("/tools")
def list_tools():
    """Geef een lijst van beschikbare tools op dit systeem."""
    available = {}
    for tool in ALLOWED_TOOLS:
        path = shutil.which(tool)
        available[tool] = {"available": path is not None, "path": path}
    return jsonify(available)


@app.post("/run")
def run_tool():
    """
    Voer een tool uit.

    Body:
        {
            "tool":   "nmap",
            "target": "192.168.1.1",
            "args":   ["-sV", "-p", "1-1000"]   // optioneel
        }

    Response:
        {
            "success":    true/false,
            "stdout":     "...",
            "stderr":     "...",
            "returncode": 0,
            "tool":       "nmap",
            "target":     "192.168.1.1"
        }
    """
    data = request.get_json(silent=True) or {}
    tool   = data.get("tool", "").strip()
    target = data.get("target", "").strip()
    args   = data.get("args", [])

    # ── Validatie ────────────────────────────────────────────────────
    if tool not in ALLOWED_TOOLS:
        return jsonify({"success": False, "error": f"Tool '{tool}' niet toegestaan"}), 400
    if not _is_safe_target(target):
        return jsonify({"success": False, "error": "Ongeldig target"}), 400
    if not isinstance(args, list):
        return jsonify({"success": False, "error": "args moet een lijst zijn"}), 400

    tool_path = shutil.which(tool)
    if not tool_path:
        return jsonify({"success": False, "error": f"Tool '{tool}' niet gevonden op dit systeem"}), 404

    # ── Bouw commando ────────────────────────────────────────────────
    cmd = [tool_path] + [str(a) for a in args] + [target]
    timeout = TOOL_TIMEOUTS.get(tool, TOOL_TIMEOUTS["default"])

    logger.info("Uitvoeren: %s  (timeout=%ds)", " ".join(shlex.quote(c) for c in cmd), timeout)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return jsonify({
            "success":    proc.returncode == 0,
            "stdout":     proc.stdout,
            "stderr":     proc.stderr,
            "returncode": proc.returncode,
            "tool":       tool,
            "target":     target,
        })
    except subprocess.TimeoutExpired:
        logger.warning("Timeout voor %s op %s", tool, target)
        return jsonify({"success": False, "error": f"Tool timeout na {timeout}s"}), 504
    except Exception as e:
        logger.error("Fout bij uitvoeren van %s: %s", tool, e)
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Luister alleen op het interne netwerk, NIET op 0.0.0.0 in productie
    host = os.getenv("TOOL_API_HOST", "192.168.121.28")
    port = int(os.getenv("TOOL_API_PORT", "5001"))
    logger.info("CyberPulse Tool API gestart op %s:%d", host, port)
    app.run(host=host, port=port, debug=False)
