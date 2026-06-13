"""Target management endpoints — school project, no auth/verification required."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_client_ip
from app.models.target import Target
from app.models.user import User
from app.services.audit import log_action

router = APIRouter(prefix="/targets", tags=["targets"])

_STUDENT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _student_user(db: AsyncSession) -> User:
    """Return the single school-project student user, creating it if needed."""
    result = await db.execute(select(User).where(User.id == _STUDENT_USER_ID))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(
        id=_STUDENT_USER_ID,
        clerk_id="student",
        email="student@cyberpulse.local",
        full_name="Student",
        plan="professional",
        credits=9999,
        max_concurrent_scans=10,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/")
async def create_target(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _student_user(db)

    # Accept both 'value'/'hostname' and both 'name'/'hostname' field names
    value = body.get("value") or body.get("hostname") or body.get("url") or ""
    name  = body.get("name")  or body.get("hostname") or value
    if not value:
        raise HTTPException(status_code=400, detail="Target value/hostname is required")

    # Map frontend target_type names to backend names
    raw_type = body.get("target_type", "domain")
    type_map = {
        "web_application": "url", "web": "url",
        "api": "url", "cloud": "url",
        "network": "ip_range", "infrastructure": "ip_range",
        "windows": "ip", "linux": "ip",
    }
    target_type = type_map.get(raw_type, raw_type)
    if target_type not in ("domain", "ip", "ip_range", "url"):
        target_type = "url"  # safe fallback

    target = Target(
        user_id=user.id,
        name=name,
        target_type=target_type,
        value=value,
        scope={},
        verification_token=str(uuid.uuid4()),
        is_verified=True,  # skip verification for school project
        verified_at=datetime.now(timezone.utc),
        verification_method="auto",
    )
    db.add(target)
    await db.commit()
    await db.refresh(target)

    ip = await get_client_ip(request)
    await log_action(
        db, "target_created", ip, user_id=user.id,
        resource_type="target", resource_id=str(target.id),
    )

    return _target_dict(target)


@router.get("/")
async def list_targets(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Target).order_by(Target.created_at.desc())
    )
    targets = result.scalars().all()
    return [_target_dict(t) for t in targets]


@router.get("/{target_id}")
async def get_target(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return _target_dict(target)


@router.delete("/{target_id}")
async def delete_target(
    target_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    await db.delete(target)
    await db.commit()

    ip = await get_client_ip(request)
    await log_action(
        db, "target_deleted", ip,
        resource_type="target", resource_id=str(target_id),
    )
    return {"message": "Target deleted"}


@router.post("/{target_id}/verify")
async def verify_target(
    target_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Verify ownership via DNS TXT record or a well-known file.
    Private/loopback IPs are auto-verified (internal/demo scans)."""
    import ipaddress

    result = await db.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Doel niet gevonden")

    host = (target.value or "").strip()
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/")[0].split(":")[0]

    # Private IP → auto-verify
    try:
        ip_obj = ipaddress.ip_address(host)
        if ip_obj.is_private or ip_obj.is_loopback:
            target.is_verified = True
            target.verified_at = datetime.now(timezone.utc)
            target.verification_method = "private_ip"
            await db.commit()
            return {"verified": True}
    except ValueError:
        pass

    token = target.verification_token
    if not token:
        import secrets as _secrets
        token = _secrets.token_hex(16)
        target.verification_token = token
        await db.commit()
        await db.refresh(target)

    method = (body or {}).get("method", "dns")

    if method == "dns":
        try:
            import dns.resolver
            answers = dns.resolver.resolve(host, "TXT")
            for ans in answers:
                if f"cyberpulse-verify={token}" in str(ans):
                    target.is_verified = True
                    target.verified_at = datetime.now(timezone.utc)
                    target.verification_method = "dns_txt"
                    await db.commit()
                    return {"verified": True}
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="DNS-record niet gevonden. Controleer of het TXT-record correct is ingesteld en probeer opnieuw.")

    if method == "file":
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                resp = await client.get(f"http://{host}/.well-known/cyberpulse-verify.txt")
            if resp.status_code == 200 and token in resp.text:
                target.is_verified = True
                target.verified_at = datetime.now(timezone.utc)
                target.verification_method = "file_upload"
                await db.commit()
                return {"verified": True}
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="Bestand niet gevonden of onjuiste inhoud. Controleer en probeer opnieuw.")

    raise HTTPException(status_code=400, detail="Onbekende verificatiemethode")


def _target_dict(t: Target) -> dict:
    """Serialize a Target to a plain dict the frontend can consume."""
    return {
        "id":                   str(t.id),
        "name":                 t.name,
        "hostname":             t.value,   # alias so frontend target.hostname works
        "value":                t.value,
        "target_type":          t.target_type,
        "scope":                t.scope or {},
        "is_verified":          t.is_verified,
        "verified_at":          t.verified_at.isoformat() if t.verified_at else None,
        "verification_method":  t.verification_method,
        "verification_token":   t.verification_token,
        "created_at":           t.created_at.isoformat() if t.created_at else None,
    }
