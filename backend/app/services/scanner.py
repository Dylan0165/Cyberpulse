"""Kali VM scan orchestrator — runs tool phases via the scanner API."""

import logging

import redis as sync_redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

from app.services.tool_runner import ToolRunner, ScannerUnavailableError


# ── Phase → tools mapping ─────────────────────────────────────────────────────
# Each phase runs its tools sequentially.
# args are f-string templates — {target} is replaced at runtime.

PHASE_TOOLS: dict[str, list[tuple[str, str, int]]] = {
    # (tool_name, args_template, timeout_seconds)
    "recon": [
        ("nmap",          "-sV -sC -T4 -p 80,443,8080,8443,22,21,25,110,143,3306,5432,6379 {target}", 300),
        ("whatweb",       "-a 3 {target}", 60),
        ("theharvester",  "-d {target} -l 100 -b duckduckgo,google", 120),
        ("subfinder",     "-d {target} -silent", 120),
    ],
    "vulnerability": [
        ("nuclei",   "-u {target} -severity medium,high,critical -silent", 600),
        ("nikto",    "-h {target} -nointeractive", 300),
    ],
    "webapp": [
        ("ffuf",     "-u https://{target}/FUZZ -w /usr/share/seclists/Discovery/Web-Content/common.txt -mc 200,301,302 -t 50 -ac", 300),
        ("nikto",    "-h {target} -Tuning 1 2 3 4 5 6 7 8 9 a b -nointeractive", 300),
    ],
    "network": [
        ("nmap",     "-sV -sC -T4 -p- --min-rate 1000 {target}", 600),
        ("masscan",  "-p1-65535 --rate=1000 {target}", 120),
    ],
    "auth": [
        ("nmap",     "-p 22,21,23,3389,5900 --script auth {target}", 120),
        ("hydra",    "-L /usr/share/wordlists/metasploit/unix_users.txt -P /usr/share/wordlists/metasploit/unix_passwords.txt {target} ssh -t 4", 180),
    ],
    "ssl": [
        ("testssl.sh", "--quiet --parallel {target}", 180),
        ("httpx",      "-u {target} -tls-probe -silent", 60),
    ],
    "cloud": [
        ("nuclei",   "-u {target} -tags cloud,aws,azure,gcp -silent", 300),
    ],
    "osint": [
        ("theharvester", "-d {target} -l 200 -b duckduckgo,google,bing,twitter", 180),
        ("gitleaks",     "detect --source /tmp --no-git --report-format json", 60),
    ],
}


def get_tool_runner() -> ToolRunner:
    return ToolRunner(
        host=settings.kali_vm_host,
        port=settings.kali_vm_port,
        api_key=settings.scanner_api_key,
    )


def get_redis_client() -> sync_redis.Redis:
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


def _inject_credentials(args_template: str, credentials: dict) -> str:
    """Substitute credential placeholders into tool arg templates."""
    result = args_template
    result = result.replace("{username}", credentials.get("username", "admin"))
    result = result.replace("{password}", credentials.get("password", ""))
    result = result.replace("{bearer_token}", credentials.get("bearer_token", ""))
    return result


def run_phase(
    phase: str,
    target: str,
    scan_id: str,
    config: dict | None = None,
) -> dict[str, str]:
    """
    Run all tools for a scan phase against target.

    Writes each tool's stdout to Redis under:
        scan:{scan_id}:output:{phase}:{tool}

    Returns a dict of tool → stdout for all tools that produced output.
    """
    tools = PHASE_TOOLS.get(phase)
    if not tools:
        logger.warning("No tools defined for phase '%s' — skipping", phase)
        return {}

    runner = get_tool_runner()
    r = get_redis_client()
    outputs: dict[str, str] = {}
    credentials = (config or {}).get("credentials", {})

    for tool_name, args_template, timeout in tools:
        args = args_template.format(target=target)
        args = _inject_credentials(args, credentials)
        logger.info("[scan:%s] phase=%s tool=%s target=%s", scan_id, phase, tool_name, target)

        try:
            stdout = runner.run(tool_name, args, timeout=timeout)
        except ScannerUnavailableError as exc:
            logger.error("[scan:%s] Kali VM unreachable: %s", scan_id, exc)
            # Store error so AI analysis sees something
            stdout = f"[ERROR] Kali VM unreachable: {exc}"
        except RuntimeError as exc:
            # Tool failed or timed out on the Kali side — non-fatal, continue
            logger.warning("[scan:%s] tool %s failed: %s", scan_id, tool_name, exc)
            stdout = f"[ERROR] {exc}"
        except Exception as exc:
            logger.error("[scan:%s] unexpected error running %s: %s", scan_id, tool_name, exc)
            stdout = f"[ERROR] {exc}"

        if stdout:
            # Store in Redis — analysis_tasks.py reads these keys
            redis_key = f"scan:{scan_id}:output:{phase}:{tool_name}"
            r.setex(redis_key, 7200, stdout)  # 2 h TTL
            outputs[tool_name] = stdout

    return outputs


def check_kali_connectivity() -> dict:
    """
    Health-check endpoint helper — returns connectivity status and available tools.
    Called by the /api/health or a dedicated diagnostic endpoint.
    """
    runner = get_tool_runner()
    reachable = runner.health_check()
    return {
        "kali_vm": f"{settings.kali_vm_host}:{settings.kali_vm_port}",
        "reachable": reachable,
        "tools": runner.available_tools() if reachable else {},
    }


# ── Legacy stubs — kept so scan_tasks.py imports don't break before cleanup ───

def stop_scan_container(container_id: str) -> None:
    """No-op: Docker containers are no longer used."""
    logger.debug("stop_scan_container called (no-op): %s", container_id)
