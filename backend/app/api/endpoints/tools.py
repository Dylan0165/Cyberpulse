"""Backend API endpoints for Kali tool management.

Proxies all tool requests to the CyberPulse engine (cyberpulse-web:7823).
The CyberPulse container has direct access to Kali binaries and its own
ToolRunner registry — the backend never checks shutil.which() itself.
"""

import json
import logging
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/tools", tags=["tools"])
logger = logging.getLogger(__name__)


def _cp_url() -> str:
    return get_settings().cyberpulse_url


async def _proxy_get(path: str) -> dict:
    url = f"{_cp_url()}{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="CyberPulse engine niet bereikbaar. Controleer of de container draait.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error("CyberPulse proxy GET %s failed: %s", path, e)
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/available")
async def list_tools():
    """Return all Kali tools with real availability — sourced from CyberPulse ToolRunner registry."""
    return await _proxy_get("/api/tools/available")


@router.get("/profiles")
async def list_profiles():
    """Return all scan profiles defined in CyberPulse config."""
    return await _proxy_get("/api/tools/profiles")


@router.get("/check")
async def check_tools():
    """Quick availability check for common tools — proxied from CyberPulse."""
    try:
        return await _proxy_get("/api/tools/check")
    except HTTPException:
        return {}


# ── Tool Scan ──────────────────────────────────────────────────────

class ToolScanRequest(BaseModel):
    target: str
    tools: list[str] | None = None
    profile: str | None = None
    scan_mode: str = "blackbox"   # blackbox | graybox | whitebox


@router.post("/scan")
async def start_tool_scan(body: ToolScanRequest):
    """Start a Kali tool scan via the CyberPulse engine.

    Returns {scan_id, status, tools} immediately. Stream live output from
    GET /api/tools/scan/{scan_id}/stream.
    """
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
        logger.error("Tool scan proxy failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/scan/{scan_id}/stream")
async def stream_tool_scan(scan_id: str):
    """Proxy the SSE event stream from CyberPulse to the frontend.

    Events: tool_start, tool_done, tool_skipped, tool_error, tools_complete, all_done
    """
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
        except httpx.ConnectError:
            msg = json.dumps({"type": "error", "message": "CyberPulse engine verbinding verbroken"})
            yield f"data: {msg}\n\n".encode()
        except Exception as e:
            logger.error("SSE proxy for %s failed: %s", safe_id, e)
            msg = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {msg}\n\n".encode()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
