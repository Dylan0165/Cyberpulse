"""Backend API endpoints for Kali tool management.

GET /api/tools/available proxies directly to the Kali VM scanner API
and enriches the response with phase/category metadata from the registry.
"""

import json
import logging
from typing import AsyncGenerator, Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/tools", tags=["tools"])
logger = logging.getLogger(__name__)


def _kali_url() -> str:
    s = get_settings()
    return f"http://{s.kali_vm_host}:{s.kali_vm_port}"


def _kali_headers() -> dict:
    key = get_settings().scanner_api_key
    return {"x-api-key": key} if key else {}


async def _kali_get(path: str, timeout: float = 15.0) -> dict:
    url = f"{_kali_url()}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=_kali_headers())
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Kali VM niet bereikbaar op {_kali_url()}. "
                   "Controleer of tool_api.py draait als service op de Kali VM.",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error("Kali VM GET %s failed: %s", path, e)
        raise HTTPException(status_code=502, detail=str(e))


def _cp_url() -> str:
    return get_settings().cyberpulse_url


async def _proxy_cp_get(path: str) -> dict:
    """Fallback proxy to the cyberpulse engine for scan SSE streams."""
    url = f"{_cp_url()}{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="CyberPulse engine niet bereikbaar.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error("CyberPulse proxy GET %s failed: %s", path, e)
        raise HTTPException(status_code=502, detail=str(e))


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/available")
async def list_available_tools():
    """
    Return all tools on the Kali VM with availability + phase/category metadata.

    The frontend tools page renders this directly: each tool shows
    name, available (bool), category, phase, description, and resource profile.
    """
    raw = await _kali_get("/tools")

    # raw is already enriched with metadata from tool_registry.py on the Kali VM
    # Shape:  { "nmap": { "available": true, "category": "recon", "phase": 1, ... } }
    # Reformat to match the ToolInfo interface expected by the frontend:
    result = {}
    for name, info in raw.items():
        result[name] = {
            "name":         name,
            "display_name": info.get("display_name") or name.replace("-", " ").title(),
            "category":     info.get("category", "recon"),
            "phase":        info.get("phase", 1),
            "available":    info.get("available", False),
            "description":  info.get("description", ""),
            "implementation": "subprocess",
            "default_timeout": info.get("estimated_duration_s", 120),
            "resource_profile": {
                "estimated_ram_mb":    info.get("estimated_ram_mb", 64),
                "estimated_duration_s": info.get("estimated_duration_s", 120),
                "requires_gpu":        info.get("requires_gpu", False),
                "cpu_intensive":       info.get("cpu_intensive", False),
            },
        }
    return result


@router.get("/profiles")
async def list_profiles():
    """Scan profiles grouped by use-case."""
    return {
        "quick_recon":      ["nmap", "whatweb", "httpx", "subfinder"],
        "web_full":         ["nmap", "nikto", "nuclei", "gobuster", "sqlmap", "xsstrike", "dalfox"],
        "network_audit":    ["nmap", "masscan", "enum4linux", "smbmap", "snmpwalk"],
        "auth_test":        ["hydra", "medusa", "kerbrute", "crackmapexec"],
        "ssl_tls":          ["testssl.sh", "sslyze", "sslscan"],
        "osint_secrets":    ["theharvester", "gitleaks", "trufflehog", "subfinder"],
        "full_pentest":     ["nmap", "nuclei", "nikto", "gobuster", "sqlmap", "hydra", "testssl.sh", "theharvester"],
    }


@router.get("/check")
async def check_tools():
    """Quick reachability check for the Kali VM."""
    try:
        url = f"{_kali_url()}/health"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=_kali_headers())
        return {"kali_vm": _kali_url(), "reachable": resp.ok}
    except Exception:
        return {"kali_vm": _kali_url(), "reachable": False}


# ── Tool scan (proxied to cyberpulse engine for SSE) ──────────────────────────

class ToolScanRequest(BaseModel):
    target: str
    tools: list[str] | None = None
    profile: str | None = None
    scan_mode: str = "blackbox"


@router.post("/scan")
async def start_tool_scan(body: ToolScanRequest):
    url = f"{_cp_url()}/api/tools/scan"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=body.model_dump())
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="CyberPulse engine niet bereikbaar")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/scan/{scan_id}/stream")
async def stream_tool_scan(scan_id: str):
    safe_id = "".join(c for c in scan_id if c.isalnum() or c in "-_")
    if safe_id != scan_id or not safe_id:
        raise HTTPException(status_code=400, detail="Ongeldig scan ID")

    upstream = f"{_cp_url()}/api/scan/{safe_id}/stream"

    async def event_stream() -> AsyncGenerator[bytes, None]:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", upstream) as resp:
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            yield chunk
        except Exception as e:
            msg = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {msg}\n\n".encode()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
