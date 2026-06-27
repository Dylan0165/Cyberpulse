"""Public demo scan for the marketing site — no auth.

Target is ALWAYS scanme.nmap.org (public nmap test host). Rate limited per IP.
Runs a short, limited scan via the Kali scanner in a background task and stores
progress on the demo_scans row; the marketing page polls GET /api/demo/{id}.
"""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.core.database import async_session
from app.core.ratelimit import limiter
from app.models.demo_scan import DemoScan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_TARGET = "scanme.nmap.org"
MAX_VISIBLE_FINDINGS = 5
_PORT_RE = re.compile(r"^(\d+)/(tcp|udp)\s+open\s+(\S+)(.*)$", re.MULTILINE)


async def _run_demo(scan_id: uuid.UUID) -> None:
    """Background: run a limited scan and store output/findings. Never raises."""
    output: list[str] = []
    findings: list[dict] = []
    try:
        from app.services.tool_runner import AsyncToolRunner
        runner = AsyncToolRunner()

        output.append(f"$ nmap -sV --top-ports 100 {DEMO_TARGET}")
        nmap = await runner.run_tool("nmap", f"-sV --top-ports 100 {DEMO_TARGET}", timeout=120)
        output.append(nmap.stdout or nmap.error or "")
        for m in _PORT_RE.finditer(nmap.stdout or ""):
            port, proto, service = m.group(1), m.group(2), m.group(3)
            findings.append({
                "type": "open_port", "severity": "INFO",
                "title": f"Open poort {port}/{proto} ({service})",
                "description": f"Service {service.strip()} detecteerbaar op poort {port}.",
            })

        output.append(f"\n$ nuclei -u {DEMO_TARGET} -severity critical,high")
        try:
            nuc = await runner.run_tool("nuclei", f"-u {DEMO_TARGET} -severity critical,high -silent", timeout=120)
            if nuc.stdout:
                output.append(nuc.stdout)
                for line in nuc.stdout.splitlines():
                    if line.strip():
                        findings.append({
                            "type": "cve", "severity": "HIGH",
                            "title": line.strip()[:120],
                            "description": "Gedetecteerd door nuclei.",
                        })
        except Exception:
            output.append("(nuclei niet beschikbaar — overgeslagen)")

        status = "completed"
    except Exception as exc:  # noqa: BLE001
        logger.warning("demo scan %s failed: %s", scan_id, exc)
        output.append(f"\nDemo gestopt: {exc}")
        status = "failed"

    try:
        async with async_session() as db:
            res = await db.execute(select(DemoScan).where(DemoScan.id == scan_id))
            row = res.scalar_one_or_none()
            if row:
                row.terminal_output = "\n".join(output)[:20000]
                row.findings = findings
                row.status = status
                row.completed_at = datetime.now(timezone.utc)
                await db.commit()
    except Exception:
        logger.exception("could not persist demo scan %s", scan_id)


@router.post("/start")
@limiter.limit("3/hour")
async def start_demo(request: Request):
    """Start a public demo scan against scanme.nmap.org (rate limited 3/uur/IP)."""
    ws_token = secrets.token_urlsafe(24)
    async with async_session() as db:
        row = DemoScan(ip_address=DEMO_TARGET, status="running", ws_token=ws_token, findings=[])
        db.add(row)
        await db.commit()
        await db.refresh(row)
        scan_id = row.id

    # Fire-and-forget background execution.
    asyncio.create_task(_run_demo(scan_id))
    return {"demo_scan_id": str(scan_id), "ws_token": ws_token, "target": DEMO_TARGET}


@router.get("/{demo_scan_id}")
async def get_demo(demo_scan_id: uuid.UUID):
    async with async_session() as db:
        res = await db.execute(select(DemoScan).where(DemoScan.id == demo_scan_id))
        row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Demo scan niet gevonden")

    all_findings = row.findings or []
    return {
        "id": str(row.id),
        "status": row.status,
        "target": row.ip_address,
        "terminal_output": row.terminal_output or "",
        "findings": all_findings[:MAX_VISIBLE_FINDINGS],
        "total_findings": len(all_findings),
        "locked_findings": max(0, len(all_findings) - MAX_VISIBLE_FINDINGS),
    }
