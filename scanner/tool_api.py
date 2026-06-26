"""
CyberPulse Scanner API — runs on the Kali VM at 192.168.121.28:5001

Dynamically discovers all installed security tools and runs them
as async subprocesses on demand.

Start:
    export SCANNER_API_KEY=changeme
    uvicorn tool_api:app --host 0.0.0.0 --port 5001
"""

import asyncio
import json
import os
import re
import shlex
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel

try:
    from tool_registry import TOOL_REGISTRY, get_tool_meta
except ImportError:
    TOOL_REGISTRY = {}  # type: ignore
    def get_tool_meta(name): return {"category": "recon", "phase": 1, "display_name": name, "description": "", "estimated_ram_mb": 64, "estimated_duration_s": 120, "requires_gpu": False, "cpu_intensive": False}  # type: ignore

# ── Auth ──────────────────────────────────────────────────────────────────────

SCANNER_API_KEY = os.getenv("SCANNER_API_KEY", "")

_SAFE_NAME = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

# Search paths for binaries
_BINARY_PATHS = [
    "/usr/bin", "/usr/local/bin", "/usr/sbin", "/usr/local/sbin",
    "/bin", "/sbin",
    "/opt/nuclei", "/opt/subfinder", "/opt/httpx", "/opt/ffuf",
    "/opt/feroxbuster", "/opt/gitleaks", "/opt/trufflehog",
    "/usr/share/metasploit-framework/",
    "/root/go/bin", "/home/kali/go/bin",
]

# Per-tool default timeouts (caps the requested timeout)
_MAX_TIMEOUTS: dict[str, int] = {
    "nuclei": 600, "sqlmap": 600, "amass": 600,
    "hashcat": 3600, "john": 1800,
    "default": 600,
}

# Per-module rate limiting — a courtesy pre-run delay so we don't hammer a
# target (and trip its own rate limiting). Tunable per tool.
MODULE_RATE_LIMITS: dict[str, dict] = {
    "nmap":    {"delay_ms": 100,  "max_rps": 10},
    "nuclei":  {"delay_ms": 200,  "max_rps": 5},
    "sqlmap":  {"delay_ms": 500,  "max_rps": 2},
    "hydra":   {"delay_ms": 1000, "max_rps": 1},
    "ffuf":    {"delay_ms": 50,   "max_rps": 20},
    "nikto":   {"delay_ms": 300,  "max_rps": 3},
    "testssl": {"delay_ms": 0,    "max_rps": 1},
    "default": {"delay_ms": 200,  "max_rps": 5},
}


def _check_key(x_api_key: Optional[str] = None):
    if not SCANNER_API_KEY:
        return
    if x_api_key != SCANNER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Api-Key header",
        )


# ── Dynamic tool discovery ────────────────────────────────────────────────────

def _discover_tools() -> dict[str, dict]:
    """
    Scan the system for all installed security tools.

    For each known tool in the registry, check if its binary exists.
    Also scan common binary directories for any executable that matches
    a known tool name.

    Returns a dict of tool_name → {available, path, ...metadata}
    """
    found: dict[str, dict] = {}

    # Check all tools in the registry
    for name, meta in TOOL_REGISTRY.items():
        path = shutil.which(name)
        # Some tools have unusual paths or wrapper scripts
        if not path:
            for base in _BINARY_PATHS:
                candidate = os.path.join(base, name)
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    path = candidate
                    break
        found[name] = {
            "available": path is not None,
            "path": path,
            **meta,
        }

    # Scan binary dirs for executables not in the registry
    for base in _BINARY_PATHS[:6]:  # only standard paths for extra scan
        if not os.path.isdir(base):
            continue
        try:
            for entry in os.scandir(base):
                if entry.name in found:
                    continue
                if not _SAFE_NAME.match(entry.name):
                    continue
                if entry.is_file() and os.access(entry.path, os.X_OK):
                    # Only include tools that look like security tools
                    # (skip common system binaries)
                    _SYSTEM_BINS = {
                        "ls","cat","cp","mv","rm","grep","sed","awk","find",
                        "sort","uniq","wc","head","tail","cut","tr","echo",
                        "bash","sh","dash","zsh","python","python3","perl",
                        "ruby","java","gcc","make","apt","dpkg","systemctl",
                        "kill","ps","top","df","du","mount","umount","dd",
                        "tar","gzip","gunzip","zip","unzip","curl","wget",
                        "ssh","scp","rsync","ping","traceroute","netstat",
                        "ip","ifconfig","route","iptables","ufw",
                    }
                    if entry.name not in _SYSTEM_BINS:
                        meta = get_tool_meta(entry.name)
                        found[entry.name] = {
                            "available": True,
                            "path": entry.path,
                            **meta,
                        }
        except PermissionError:
            continue

    return found


# Cache tool discovery for 5 minutes
_tool_cache: dict = {}
_cache_time: float = 0.0


def get_tools(force_refresh: bool = False) -> dict[str, dict]:
    import time
    global _tool_cache, _cache_time
    if force_refresh or time.time() - _cache_time > 300:
        _tool_cache = _discover_tools()
        _cache_time = time.time()
    return _tool_cache


# ── Job store ─────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    RUNNING = "running"
    DONE    = "done"
    FAILED  = "failed"


class Job:
    def __init__(self, job_id: str, tool: str, args: str):
        self.job_id     = job_id
        self.tool       = tool
        self.args       = args
        self.status     = JobStatus.RUNNING
        self.stdout     = ""
        self.stderr     = ""
        self.returncode: Optional[int] = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.finished_at: Optional[str] = None
        self._process: Optional[asyncio.subprocess.Process] = None

    def to_dict(self) -> dict:
        return {
            "job_id":      self.job_id,
            "tool":        self.tool,
            "args":        self.args,
            "status":      self.status,
            "stdout":      self.stdout,
            "stderr":      self.stderr,
            "returncode":  self.returncode,
            "created_at":  self.created_at,
            "finished_at": self.finished_at,
        }


_jobs: dict[str, Job] = {}


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="CyberPulse Scanner API", version="2.0")

# Write a small demo password wordlist on startup so hydra can always find it.
# Contains common defaults including root:toor used on the school pentest target.
_CYBER_PASSWORDS = "\n".join([
    "root", "toor", "admin", "password", "password123",
    "123456", "12345678", "test", "kali", "ubuntu",
    "changeme", "letmein", "qwerty", "abc123", "default",
    "1234", "P@ssw0rd", "Admin123", "welcome",
])
try:
    os.makedirs("/opt/cyberpulse", exist_ok=True)
    # Only write if missing — preserves any manually curated wordlist.
    if not os.path.exists("/opt/cyberpulse/passwords.txt"):
        with open("/opt/cyberpulse/passwords.txt", "w") as _f:
            _f.write(_CYBER_PASSWORDS + "\n")
except Exception:
    pass


class RunToolRequest(BaseModel):
    tool:    str
    args:    str = ""
    timeout: int = 300


# ── Background task ───────────────────────────────────────────────────────────

async def _execute(job: Job, tool_path: str, timeout: int):
    extra = shlex.split(job.args) if job.args.strip() else []
    cmd   = [tool_path] + extra

    # Per-module courtesy rate limit (small pre-run delay).
    rl = MODULE_RATE_LIMITS.get(job.tool, MODULE_RATE_LIMITS["default"])
    if rl.get("delay_ms"):
        await asyncio.sleep(rl["delay_ms"] / 1000)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        job._process = proc

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout)
            )
            job.stdout     = stdout_bytes.decode(errors="replace")
            job.stderr     = stderr_bytes.decode(errors="replace")
            job.returncode = proc.returncode
            job.status     = JobStatus.DONE if proc.returncode == 0 else JobStatus.FAILED
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            job.status     = JobStatus.FAILED
            job.stderr     = f"Timeout: tool exceeded {timeout}s"
            job.returncode = -1

    except Exception as exc:
        job.status     = JobStatus.FAILED
        job.stderr     = str(exc)
        job.returncode = -1

    job.finished_at = datetime.now(timezone.utc).isoformat()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "node": "kali-tool-api"}


@app.get("/tools")
async def list_tools(
    refresh: bool = False,
    x_api_key: Optional[str] = Header(default=None),
):
    """Return all tools found on this system with their availability and metadata."""
    _check_key(x_api_key)
    tools = get_tools(force_refresh=refresh)
    # Return only name → {available, category, phase, description, ...}
    return {
        name: {
            "available":          info["available"],
            "category":           info.get("category", "recon"),
            "phase":              info.get("phase", 1),
            "display_name":       info.get("display_name", name),
            "description":        info.get("description", ""),
            "estimated_ram_mb":   info.get("estimated_ram_mb", 64),
            "estimated_duration_s": info.get("estimated_duration_s", 120),
            "requires_gpu":       info.get("requires_gpu", False),
            "cpu_intensive":      info.get("cpu_intensive", False),
        }
        for name, info in tools.items()
    }


@app.post("/run-tool", status_code=status.HTTP_202_ACCEPTED)
async def run_tool(
    body: RunToolRequest,
    x_api_key: Optional[str] = Header(default=None),
):
    _check_key(x_api_key)

    # Validate tool name
    if not _SAFE_NAME.match(body.tool):
        raise HTTPException(status_code=400, detail="Invalid tool name")

    # Resolve binary
    tools = get_tools()
    tool_info = tools.get(body.tool)

    if tool_info and tool_info["available"] and tool_info.get("path"):
        tool_path = tool_info["path"]
    else:
        # Try a fresh lookup
        tool_path = shutil.which(body.tool)
        if not tool_path:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{body.tool}' not found on this system",
            )

    max_timeout = _MAX_TIMEOUTS.get(body.tool, _MAX_TIMEOUTS["default"])
    effective_timeout = min(max(body.timeout, 10), max_timeout)

    job_id = str(uuid.uuid4())
    job = Job(job_id=job_id, tool=body.tool, args=body.args)
    _jobs[job_id] = job

    asyncio.create_task(_execute(job, tool_path, effective_timeout))
    return {"job_id": job_id}


@app.get("/job/{job_id}")
async def get_job(
    job_id: str,
    x_api_key: Optional[str] = Header(default=None),
):
    _check_key(x_api_key)
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@app.delete("/job/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    x_api_key: Optional[str] = Header(default=None),
):
    _check_key(x_api_key)
    job = _jobs.pop(job_id, None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job._process and job.status == JobStatus.RUNNING:
        try:
            job._process.kill()
        except Exception:
            pass


@app.post("/tools/refresh", status_code=status.HTTP_200_OK)
async def refresh_tools(x_api_key: Optional[str] = Header(default=None)):
    """Force re-scan of installed tools (invalidates 5-minute cache)."""
    _check_key(x_api_key)
    tools = get_tools(force_refresh=True)
    available = sum(1 for t in tools.values() if t["available"])
    return {"total": len(tools), "available": available}


# ── Subdomain discovery ───────────────────────────────────────────────────────
# Combines theHarvester + crt.sh (Certificate Transparency) + a small DNS
# brute force, dedupes, then keeps only hosts that are alive (nmap -sn).
# Every stage degrades gracefully — a missing tool or a timeout is skipped, and
# the endpoint never raises a 500.

_SAFE_DOMAIN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$")
_IPV4 = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

_DNS_WORDLIST = [
    "www", "mail", "ftp", "vpn", "api", "app", "dev", "staging",
    "test", "admin", "portal", "remote", "ssh", "cdn", "ns1", "ns2",
    "smtp", "pop", "imap", "webmail", "cloud", "git", "gitlab", "jenkins",
]


class SubdomainRequest(BaseModel):
    domain: str
    api_key: Optional[str] = None  # accepted for compatibility; header is authoritative


async def _run_cmd(cmd: list[str], timeout: int) -> tuple[int, str, str]:
    """Run a command (no shell), capturing output. Never raises."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return -1, "", "binary not found"
    except Exception as exc:  # noqa: BLE001
        return -1, "", str(exc)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=float(timeout))
        return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        return -1, "", f"timeout after {timeout}s"


async def _sd_theharvester(domain: str) -> set[str]:
    binary = shutil.which("theHarvester") or shutil.which("theharvester")
    if not binary:
        return set()
    out_base = f"/tmp/harvest_{uuid.uuid4().hex}"
    _, out, err = await _run_cmd(
        [binary, "-d", domain, "-b", "all", "-l", "500", "-f", out_base], 120
    )
    pattern = re.compile(r"([a-z0-9][a-z0-9-]*\.)+" + re.escape(domain))
    subs = {m.group(0).strip(".") for m in pattern.finditer((out + "\n" + err).lower())}
    # Also try the JSON file theHarvester writes, if present.
    for ext in (".json",):
        try:
            with open(out_base + ext, "r", errors="replace") as fh:
                for m in pattern.finditer(fh.read().lower()):
                    subs.add(m.group(0).strip("."))
        except Exception:
            pass
    return subs


async def _sd_crtsh(domain: str) -> set[str]:
    _, out, _ = await _run_cmd(
        ["curl", "-s", "--max-time", "30", f"https://crt.sh/?q=%.{domain}&output=json"], 35
    )
    subs: set[str] = set()
    try:
        for row in json.loads(out or "[]"):
            for name in str(row.get("name_value", "")).splitlines():
                name = name.strip().lower().lstrip("*.")
                if name.endswith(domain) and "@" not in name and "*" not in name:
                    subs.add(name)
    except Exception:
        pass  # malformed / empty / timeout → skip
    return subs


async def _sd_dns_bruteforce(domain: str) -> set[str]:
    found: set[str] = set()

    async def _check(entry: str) -> None:
        host = f"{entry}.{domain}"
        _, out, _ = await _run_cmd(["dig", "+short", host], 10)
        if _IPV4.search(out or ""):
            found.add(host)

    await asyncio.gather(*[_check(e) for e in _DNS_WORDLIST])
    return found


async def _sd_alive(subs: list[str]) -> list[str]:
    """Keep only subdomains nmap reports as up (-sn ping sweep)."""
    if not subs:
        return []
    _, out, _ = await _run_cmd(["nmap", "-sn", "-T4"] + subs, 180)
    alive: set[str] = set()
    sub_set = set(subs)
    # Each block: "Nmap scan report for <host> (<ip>)\n... Host is up ..."
    for block in out.split("Nmap scan report for ")[1:]:
        host = block.split()[0].strip("()").lower()
        if "host is up" in block.lower() and host in sub_set:
            alive.add(host)
    return sorted(alive)


@app.post("/subdomain-discovery")
async def subdomain_discovery(
    body: SubdomainRequest,
    x_api_key: Optional[str] = Header(default=None),
):
    _check_key(x_api_key)
    domain = (body.domain or "").strip().lower().lstrip("*.").rstrip("/")
    if not _SAFE_DOMAIN.match(domain):
        return {"domain": domain, "subdomains": [], "total_found": 0,
                "total_alive": 0, "sources": {}, "error": "invalid domain"}

    # Run the three sources concurrently; each is individually fault-tolerant.
    harvester, crtsh, brute = await asyncio.gather(
        _sd_theharvester(domain), _sd_crtsh(domain), _sd_dns_bruteforce(domain),
        return_exceptions=True,
    )
    h = harvester if isinstance(harvester, set) else set()
    c = crtsh if isinstance(crtsh, set) else set()
    d = brute if isinstance(brute, set) else set()

    found = sorted((h | c | d | {domain}))
    sources = {"theharvester": len(h), "crt_sh": len(c), "dns_bruteforce": len(d)}

    try:
        alive = await _sd_alive(found)
    except Exception:
        alive = found  # degrade gracefully — better to return found than nothing

    return {
        "domain": domain,
        "subdomains": alive,
        "total_found": len(found),
        "total_alive": len(alive),
        "sources": sources,
    }
