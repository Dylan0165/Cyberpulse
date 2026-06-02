"""Report export endpoints — PDF, JSON, CSV, XML."""

import csv
import io
import json
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_client_ip
from app.core.redis import get_redis
from app.models.scan import Scan
from app.models.target import Target
from app.models.user import User
from app.reports.pdf_generator import generate_pdf_report
from app.services.audit import log_action

router = APIRouter(prefix="/reports", tags=["reports"])


async def _get_user(db: AsyncSession, clerk_id: str) -> User:
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def _get_report_data(scan: Scan, scan_id: uuid.UUID) -> dict | None:
    """Get report data from DB or Redis."""
    if scan.report_data:
        return scan.report_data

    redis = await get_redis()
    cached = await redis.get(f"scan:{scan_id}:report")
    if cached:
        return json.loads(cached)

    return None


@router.get("/{scan_id}/pdf")
async def export_pdf(
    scan_id: uuid.UUID,
    request: Request,
    white_label: bool = Query(False),
    company_name: str = Query(""),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])

    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    report_data = await _get_report_data(scan, scan_id)
    if not report_data:
        raise HTTPException(status_code=404, detail="Report not available")

    target_result = await db.execute(select(Target).where(Target.id == scan.target_id))
    target = target_result.scalar_one_or_none()
    target_value = target.value if target else "Unknown"

    pdf_bytes = generate_pdf_report(
        report_data=report_data,
        target=target_value,
        scan_type=scan.scan_type,
        white_label=white_label,
        company_name=company_name,
    )

    ip = await get_client_ip(request)
    await log_action(
        db, "report_exported", ip, user_id=user.id,
        resource_type="scan", resource_id=str(scan_id),
        details={"format": "pdf", "white_label": white_label},
    )

    filename = f"autopentest_report_{target_value}_{scan.created_at.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{scan_id}/json")
async def export_json(
    scan_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    report_data = await _get_report_data(scan, scan_id)
    if not report_data:
        raise HTTPException(status_code=404, detail="Report not available")

    ip = await get_client_ip(request)
    await log_action(
        db, "report_exported", ip, user_id=user.id,
        resource_type="scan", resource_id=str(scan_id),
        details={"format": "json"},
    )

    output = json.dumps(report_data, indent=2, default=str)
    return StreamingResponse(
        io.BytesIO(output.encode()),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="report_{scan_id}.json"'},
    )


@router.get("/{scan_id}/csv")
async def export_csv(
    scan_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    report_data = await _get_report_data(scan, scan_id)
    if not report_data:
        raise HTTPException(status_code=404, detail="Report not available")

    ip = await get_client_ip(request)
    await log_action(
        db, "report_exported", ip, user_id=user.id,
        resource_type="scan", resource_id=str(scan_id),
        details={"format": "csv"},
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Title", "Risk Level", "CVSS Score", "CVE IDs",
        "Affected Asset", "Phase", "Tool", "OWASP Category",
        "Business Impact", "Estimated Fix Time",
    ])

    for finding in report_data.get("findings", []):
        writer.writerow([
            finding.get("id", ""),
            finding.get("title", ""),
            finding.get("risk_level", ""),
            finding.get("cvss_score", ""),
            ", ".join(finding.get("cve_ids", [])),
            finding.get("affected_asset", ""),
            finding.get("phase", ""),
            finding.get("tool", ""),
            finding.get("owasp_category", ""),
            finding.get("business_impact", ""),
            finding.get("estimated_fix_time", ""),
        ])

    csv_bytes = output.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report_{scan_id}.csv"'},
    )


@router.get("/{scan_id}/xml")
async def export_xml(
    scan_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    report_data = await _get_report_data(scan, scan_id)
    if not report_data:
        raise HTTPException(status_code=404, detail="Report not available")

    ip = await get_client_ip(request)
    await log_action(
        db, "report_exported", ip, user_id=user.id,
        resource_type="scan", resource_id=str(scan_id),
        details={"format": "xml"},
    )

    root = ET.Element("SecurityReport")
    ET.SubElement(root, "ScanId").text = str(scan_id)
    ET.SubElement(root, "OverallScore").text = str(report_data.get("overall_score", 0))
    ET.SubElement(root, "ExecutiveSummary").text = report_data.get("executive_summary", "")

    findings_el = ET.SubElement(root, "Findings")
    for finding in report_data.get("findings", []):
        f_el = ET.SubElement(findings_el, "Finding")
        ET.SubElement(f_el, "Id").text = finding.get("id", "")
        ET.SubElement(f_el, "Title").text = finding.get("title", "")
        ET.SubElement(f_el, "RiskLevel").text = finding.get("risk_level", "")
        ET.SubElement(f_el, "CVSSScore").text = str(finding.get("cvss_score", ""))
        ET.SubElement(f_el, "AffectedAsset").text = finding.get("affected_asset", "")
        ET.SubElement(f_el, "Description").text = finding.get("description", "")

    xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=True).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(xml_bytes),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="report_{scan_id}.xml"'},
    )
