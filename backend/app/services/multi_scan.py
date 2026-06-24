"""MultiScanOrchestrator — fan a CIDR / IP range / domain into per-host scans.

Discovery (alive hosts / subdomains) runs against the Kali scanner with a safe
fallback so a missing scanner never hard-fails a preview. Credits are deducted
atomically (SELECT FOR UPDATE via CreditsService) before any scan is queued.
"""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.target import Target
from app.models.scan import Scan
from app.models.multi_scan import MultiScanJob
from app.schemas.scan import QUICK_PHASES
from app.services.target_parser import TargetParser
from app.services.subdomain_discovery import discover_subdomains
from app.services.credits import credits_service

logger = logging.getLogger(__name__)

_NMAP_REPORT_RE = re.compile(r"Nmap scan report for (?:[\w.-]+ \()?(\d+\.\d+\.\d+\.\d+)\)?")


async def _alive_hosts(hosts: list[str]) -> list[str]:
    """Ping-sweep via the scanner (nmap -sn). Falls back to all hosts."""
    if not hosts:
        return []
    try:
        from app.services.tool_runner import AsyncToolRunner

        runner = AsyncToolRunner()
        # Sweep the whole list in one nmap call.
        result = await runner.run_tool("nmap", f"-sn {' '.join(hosts)}", timeout=120)
        found = _NMAP_REPORT_RE.findall(result.stdout or "")
        alive = [h for h in hosts if h in set(found)]
        if alive:
            return alive
    except Exception as exc:  # noqa: BLE001 — discovery is best-effort
        logger.warning("ping sweep unavailable, assuming all hosts alive: %s", exc)
    # Fallback: treat every parsed host as alive so the feature still works.
    return hosts


class MultiScanOrchestrator:
    async def preview(self, user_id: uuid.UUID, target: str, db: AsyncSession) -> dict:
        """Discovery-only preview — no scans started, no credits deducted."""
        parsed = TargetParser.parse(target)
        ptype = parsed["type"]

        if ptype in ("cidr", "range"):
            alive = await _alive_hosts(parsed.get("hosts", []))
        elif ptype == "domain_with_subs":
            alive = await discover_subdomains(parsed["domain"])
        else:
            alive = [parsed["value"]]

        required = TargetParser.credits_for_hosts(len(alive))
        balance = await credits_service.get_balance(db, user_id)
        available = balance["credits_remaining"]
        return {
            "type": ptype,
            "input": target,
            "alive_hosts": alive,
            "estimated_hosts": len(alive),
            "credits_required": required,
            "credits_available": available,
            "can_afford": balance["is_unlimited"] or available >= required,
        }

    async def start(self, user_id: uuid.UUID, target: str, db: AsyncSession) -> dict:
        """Re-run discovery, deduct credits, create per-host scans, dispatch."""
        prev = await self.preview(user_id, target, db)
        alive: list[str] = prev["alive_hosts"]
        required: int = prev["credits_required"]

        if not alive:
            raise HTTPException(status_code=400, detail="Geen actieve hosts gevonden")
        if not prev["can_afford"]:
            raise HTTPException(status_code=402, detail={
                "error": "no_credits",
                "message": f"U heeft {required} credits nodig maar {prev['credits_available']} beschikbaar.",
                "buy_url": "/billing",
            })

        parsed = TargetParser.parse(target)
        job_type = "subdomain" if parsed["type"] == "domain_with_subs" else parsed["type"]

        # Parent target groups the children (CIDR/range/domain).
        parent = Target(
            user_id=user_id,
            name=target,
            target_type=parsed["type"],
            value=target,
            cidr_notation=target if parsed["type"] == "cidr" else None,
            ip_range_start=parsed.get("range_start"),
            ip_range_end=parsed.get("range_end"),
            discovered_hosts=alive,
            is_verified=True,
        )
        db.add(parent)
        await db.flush()

        job = MultiScanJob(
            user_id=user_id,
            job_type=job_type,
            input=target,
            status="scanning",
            total_hosts=len(alive),
            credits_used=required,
            scan_ids=[],
        )
        db.add(job)
        await db.flush()

        scan_ids: list[str] = []
        for host in alive:
            child = Target(
                user_id=user_id,
                name=host,
                target_type="single",
                value=host,
                parent_target_id=parent.id,
                is_verified=True,
            )
            db.add(child)
            await db.flush()
            scan = Scan(
                user_id=user_id,
                target_id=child.id,
                scan_type="quick",
                phases=list(QUICK_PHASES),
                config={"scan_mode": "safe", "target_type": "single", "multi_scan_job_id": str(job.id)},
                save_report=True,
                status="pending",
            )
            db.add(scan)
            await db.flush()
            scan_ids.append(str(scan.id))

        job.scan_ids = scan_ids

        # Deduct the tiered credits in one atomic step (tied to the first scan).
        if required > 0:
            await credits_service.deduct_credit(db, user_id, uuid.UUID(scan_ids[0]), amount=required)

        await db.commit()

        # Queue each child scan on the worker.
        try:
            from app.workers.scan_tasks import run_scan
            for sid in scan_ids:
                run_scan.delay(sid)
        except Exception as exc:  # noqa: BLE001 — queue failure shouldn't 500 the request
            logger.error("failed to enqueue one or more multi-scan tasks: %s", exc)

        return {
            "job_id": str(job.id),
            "message": f"{len(scan_ids)} scans gestart",
            "credits_used": required,
            "total_hosts": len(alive),
        }


multi_scan_orchestrator = MultiScanOrchestrator()
