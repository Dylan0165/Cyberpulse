"""Scan comparison (diff), per-target trend, and remediation checklist (Blok 8)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_required_user
from app.models.user import User
from app.models.scan import Scan
from app.models.finding_status import FindingStatus
from app.services.findings_deduplicator import stable_finding_id

router = APIRouter(tags=["analytics"])

_FIX_TIME = {"critical": "2 uur", "high": "1 uur", "medium": "30 min", "low": "15 min", "info": "5 min"}


def _risk(scan: Scan) -> int:
    if scan.security_score is not None:
        return int(round(100 - float(scan.security_score)))
    rd = scan.report_data or scan.ai_analysis or {}
    return int(rd.get("risk_score", 0) or 0)


def _key(f: dict) -> str:
    return f"{(f.get('type') or f.get('title') or '').lower()}:{f.get('port','')}"


async def _owned_scan(db: AsyncSession, scan_id: uuid.UUID, user: User) -> Scan:
    res = await db.execute(select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id))
    scan = res.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan niet gevonden")
    return scan


@router.get("/scans/{scan_id}/compare/{previous_scan_id}")
async def compare_scans(
    scan_id: uuid.UUID,
    previous_scan_id: uuid.UUID,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    cur = await _owned_scan(db, scan_id, user)
    prev = await _owned_scan(db, previous_scan_id, user)
    if cur.target_id != prev.target_id:
        raise HTTPException(status_code=400, detail="Scans horen niet bij hetzelfde systeem")

    cur_f = cur.findings or []
    prev_f = prev.findings or []
    cur_map = {_key(f): f for f in cur_f}
    prev_map = {_key(f): f for f in prev_f}

    new = [f for k, f in cur_map.items() if k not in prev_map]
    resolved = [f for k, f in prev_map.items() if k not in cur_map]
    unchanged = [f for k, f in cur_map.items() if k in prev_map]
    delta = _risk(cur) - _risk(prev)

    return {
        "new_findings": new,
        "resolved_findings": resolved,
        "unchanged_findings": unchanged,
        "risk_score_delta": delta,
        "current_risk": _risk(cur),
        "previous_risk": _risk(prev),
        "summary": (
            f"{len(new)} nieuwe bevindingen, {len(resolved)} opgelost, "
            f"risicoscore {'gedaald' if delta < 0 else 'gestegen' if delta > 0 else 'gelijk'} "
            f"van {_risk(prev)} naar {_risk(cur)}"
        ),
    }


@router.get("/targets/{target_id}/trend")
async def target_trend(
    target_id: uuid.UUID,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Scan)
        .where(Scan.target_id == target_id, Scan.user_id == user.id, Scan.status == "completed")
        .order_by(Scan.created_at.asc())
    )
    scans = res.scalars().all()
    points = [
        {
            "scan_id": str(s.id),
            "date": (s.completed_at or s.created_at).date().isoformat() if (s.completed_at or s.created_at) else None,
            "risk_score": _risk(s),
            "critical": s.critical_count or 0,
            "high": s.high_count or 0,
            "medium": getattr(s, "medium_count", 0) or 0,
            "low": getattr(s, "low_count", 0) or 0,
        }
        for s in scans
    ]
    return {"target_id": str(target_id), "points": points, "enough_data": len(points) >= 2}


@router.get("/scans/{scan_id}/remediation")
async def remediation(
    scan_id: uuid.UUID,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    scan = await _owned_scan(db, scan_id, user)
    findings = scan.findings or []

    # Merge triage statuses; exclude resolved / false positives from open work.
    ids = [f.get("id") or stable_finding_id(str(scan_id), f) for f in findings]
    smap: dict[str, str] = {}
    if ids:
        rows = await db.execute(select(FindingStatus).where(FindingStatus.finding_id.in_(ids)))
        smap = {r.finding_id: r.status for r in rows.scalars().all()}

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    items = []
    done = 0
    for f in findings:
        fid = f.get("id") or stable_finding_id(str(scan_id), f)
        status = smap.get(fid, "open")
        if status in ("resolved", "false_positive"):
            done += 1
            continue
        sev = str(f.get("severity", "info")).lower()
        items.append({
            "finding_id": fid,
            "title": f.get("title", "Bevinding"),
            "severity": sev,
            "status": status,
            "fix_time_estimate": _FIX_TIME.get(sev, "30 min"),
            "fix_command": f.get("fix_command") or f.get("recommendation") or "",
        })
    items.sort(key=lambda x: sev_order.get(x["severity"], 5))
    total = len(items) + done
    return {
        "scan_id": str(scan_id),
        "total": total,
        "resolved": done,
        "open": len(items),
        "progress": round((done / total) * 100) if total else 0,
        "items": items,
    }
