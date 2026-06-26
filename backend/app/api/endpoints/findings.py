"""Finding triage — per-finding status (open/resolved/false_positive/accepted_risk).

Findings are JSONB on scans.findings; each carries a stable `id` from the scan
pipeline. Status overrides live in the finding_statuses table and are merged
back when listing a scan's findings.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_required_user
from app.models.user import User
from app.models.scan import Scan
from app.models.finding_status import FindingStatus, VALID_STATUSES
from app.services.findings_deduplicator import stable_finding_id

router = APIRouter(tags=["findings"])


class FindingStatusUpdate(BaseModel):
    status: str
    note: str | None = None


def _ensure_ids(scan_id: str, findings: list) -> list:
    """Guarantee every finding has a stable id (older scans may lack one)."""
    out = []
    for f in findings or []:
        if isinstance(f, dict):
            if not f.get("id"):
                f = {**f, "id": stable_finding_id(scan_id, f)}
            out.append(f)
    return out


@router.patch("/findings/{finding_id}/status")
async def set_finding_status(
    finding_id: str,
    body: FindingStatusUpdate,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Ongeldige status. Toegestaan: {', '.join(VALID_STATUSES)}")

    # Find the user's scan that contains a finding with this id (JSONB @>).
    res = await db.execute(
        select(Scan).where(Scan.user_id == user.id, Scan.findings.contains([{"id": finding_id}]))
    )
    scan = res.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Bevinding niet gevonden")

    # Upsert the status row (locked to avoid a concurrent double-insert).
    existing = await db.execute(
        select(FindingStatus).where(FindingStatus.finding_id == finding_id).with_for_update()
    )
    row = existing.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        row = FindingStatus(
            finding_id=finding_id, scan_id=scan.id, user_id=user.id,
            status=body.status, status_note=body.note, status_set_at=now, status_set_by=user.id,
        )
        db.add(row)
    else:
        row.status = body.status
        row.status_note = body.note
        row.status_set_at = now
        row.status_set_by = user.id
    await db.commit()
    return {
        "finding_id": finding_id,
        "status": body.status,
        "note": body.note,
        "status_set_at": now.isoformat(),
    }


@router.get("/scans/{scan_id}/findings")
async def list_scan_findings(
    scan_id: uuid.UUID,
    status: str | None = Query(None),
    severity: str | None = Query(None),
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id))
    scan = res.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan niet gevonden")

    findings = _ensure_ids(str(scan_id), scan.findings or [])

    # Merge stored statuses.
    ids = [f["id"] for f in findings]
    status_map: dict[str, FindingStatus] = {}
    if ids:
        srows = await db.execute(select(FindingStatus).where(FindingStatus.finding_id.in_(ids)))
        status_map = {r.finding_id: r for r in srows.scalars().all()}

    merged = []
    for f in findings:
        st = status_map.get(f["id"])
        merged.append({
            **f,
            "status": st.status if st else "open",
            "status_note": st.status_note if st else None,
            "status_set_at": st.status_set_at.isoformat() if (st and st.status_set_at) else None,
        })

    if status:
        merged = [f for f in merged if f.get("status") == status]
    if severity:
        merged = [f for f in merged if str(f.get("severity", "")).lower() == severity.lower()]

    return {"scan_id": str(scan_id), "total": len(merged), "findings": merged}
