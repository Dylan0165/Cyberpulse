"""Scan project endpoints — bundle multiple targets/scans + combined report."""

from __future__ import annotations

import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_required_user
from app.models.user import User
from app.models.project import ScanProject
from app.models.scan import Scan
from app.models.target import Target
from app.services.target_parser import TargetParser
from app.services.credits import credits_service

router = APIRouter(prefix="/projects", tags=["projects"])

_SEVERITY_WEIGHT = {"critical": 40, "high": 25, "medium": 10, "low": 3, "info": 0}


class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None
    target_list: list[str]


def _expand_targets(target_list: list[str]) -> list[str]:
    """Flatten each entry to concrete hosts (CIDR/range expanded, capped)."""
    hosts: list[str] = []
    for raw in target_list:
        parsed = TargetParser.parse(raw)
        if parsed["type"] in ("cidr", "range"):
            hosts.extend(parsed.get("hosts", []))
        elif parsed["type"] == "domain_with_subs":
            hosts.append(parsed["domain"])  # discovery happens per-scan elsewhere
        else:
            hosts.append(parsed["value"])
    # De-dupe preserving order.
    seen: set[str] = set()
    return [h for h in hosts if not (h in seen or seen.add(h))]


@router.post("")
@router.post("/")
async def create_project(
    body: CreateProjectRequest,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    hosts = _expand_targets(body.target_list)
    if not hosts:
        raise HTTPException(status_code=400, detail="Geen geldige targets opgegeven")

    # Credits: 1 per host. Check up front (unlimited plans pass).
    balance = await credits_service.get_balance(db, user.id)
    if not balance["is_unlimited"] and balance["credits_remaining"] < len(hosts):
        raise HTTPException(status_code=402, detail={
            "error": "no_credits",
            "message": f"U heeft {len(hosts)} credits nodig maar {balance['credits_remaining']} beschikbaar.",
            "buy_url": "/billing",
        })

    project = ScanProject(
        user_id=user.id, name=body.name.strip() or "Project",
        description=body.description, total_scans=len(hosts),
    )
    db.add(project)
    await db.flush()

    scan_ids: list[str] = []
    for host in hosts:
        target = Target(user_id=user.id, name=host, target_type="single", value=host, is_verified=True)
        db.add(target)
        await db.flush()
        scan = Scan(
            user_id=user.id, target_id=target.id, project_id=project.id,
            scan_type="quick", phases=["recon", "vulnerability", "ssl"],
            config={"scan_mode": "safe", "target_type": "single"},
            save_report=True, status="pending",
        )
        db.add(scan)
        await db.flush()
        await credits_service.deduct_credit(db, user.id, scan.id)
        scan_ids.append(str(scan.id))

    await db.commit()

    try:
        from app.workers.scan_tasks import run_scan
        for sid in scan_ids:
            run_scan.delay(sid)
    except Exception:
        pass

    return {"project_id": str(project.id), "scans_started": len(scan_ids), "credits_used": len(scan_ids)}


def _project_dict(p: ScanProject) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "status": p.status,
        "total_scans": p.total_scans,
        "completed_scans": p.completed_scans,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


async def _load_project(db: AsyncSession, project_id: uuid.UUID, user: User) -> ScanProject:
    res = await db.execute(
        select(ScanProject).where(ScanProject.id == project_id, ScanProject.user_id == user.id)
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project niet gevonden")
    return project


async def _project_scans(db: AsyncSession, project_id: uuid.UUID) -> list[Scan]:
    res = await db.execute(select(Scan).where(Scan.project_id == project_id))
    return list(res.scalars().all())


async def _sync_progress(db: AsyncSession, project: ScanProject, scans: list[Scan]) -> None:
    completed = sum(1 for s in scans if s.status in ("completed", "failed", "cancelled"))
    if completed != project.completed_scans:
        project.completed_scans = completed
        if completed >= project.total_scans and project.status == "active":
            project.status = "completed"
        await db.commit()


@router.get("")
@router.get("/")
async def list_projects(user: User = Depends(get_required_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(ScanProject).where(ScanProject.user_id == user.id).order_by(ScanProject.created_at.desc())
    )
    return [_project_dict(p) for p in res.scalars().all()]


@router.get("/{project_id}")
async def get_project(
    project_id: uuid.UUID,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _load_project(db, project_id, user)
    scans = await _project_scans(db, project_id)
    await _sync_progress(db, project, scans)

    target_ids = {s.target_id for s in scans}
    tmap: dict = {}
    if target_ids:
        tres = await db.execute(select(Target).where(Target.id.in_(target_ids)))
        tmap = {t.id: t.value for t in tres.scalars().all()}

    return {
        **_project_dict(project),
        "scans": [
            {"scan_id": str(s.id), "host": tmap.get(s.target_id), "status": s.status,
             "risk_score": getattr(s, "risk_score", None)}
            for s in scans
        ],
    }


def _aggregate(scans: list[Scan], tmap: dict) -> dict:
    """Combine findings across all completed scans in the project."""
    all_findings: list[dict] = []
    per_host: list[dict] = []
    score_total = 0
    for s in scans:
        findings = s.findings or []
        sev_counts = {k: 0 for k in _SEVERITY_WEIGHT}
        for f in findings:
            sev = str((f or {}).get("severity", "info")).lower()
            if sev in sev_counts:
                sev_counts[sev] += 1
            if sev in ("critical", "high"):
                all_findings.append({**f, "host": tmap.get(s.target_id)})
        host_score = min(100, sum(_SEVERITY_WEIGHT[k] * v for k, v in sev_counts.items()))
        score_total += host_score
        per_host.append({
            "host": tmap.get(s.target_id),
            "status": s.status,
            "findings": len(findings),
            "severity_counts": sev_counts,
            "risk_score": host_score,
        })
    avg_score = round(score_total / len(scans)) if scans else 0
    return {
        "risk_score": avg_score,
        "critical_high_findings": all_findings,
        "per_host": per_host,
        "total_findings": sum(h["findings"] for h in per_host),
    }


@router.get("/{project_id}/report")
async def project_report(
    project_id: uuid.UUID,
    format: str = Query("json"),
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _load_project(db, project_id, user)
    scans = await _project_scans(db, project_id)
    target_ids = {s.target_id for s in scans}
    tmap: dict = {}
    if target_ids:
        tres = await db.execute(select(Target).where(Target.id.in_(target_ids)))
        tmap = {t.id: t.value for t in tres.scalars().all()}

    combined = _aggregate(scans, tmap)
    report = {"project": _project_dict(project), **combined}

    if format == "pdf":
        try:
            from app.reports.pdf_generator import generate_pdf_report
            report_data = {
                "summary": {
                    "risk_score": combined["risk_score"],
                    "total_findings": combined["total_findings"],
                },
                "findings": combined["critical_high_findings"],
                "hosts": combined["per_host"],
            }
            pdf_bytes = generate_pdf_report(
                report_data=report_data, target=project.name, scan_type="project",
            )
            return StreamingResponse(
                io.BytesIO(pdf_bytes), media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="project_{project.name}.pdf"'},
            )
        except Exception:
            # PDF generation is best-effort; fall back to JSON.
            pass

    return report
