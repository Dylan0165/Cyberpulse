"""Admin API — user & subscription management for the Scanix backend.

Admin-only (role == 'admin'), except POST /admin/init which bootstraps the
first admin. Dutch error messages, English code/logs. Async SQLAlchemy
throughout. Never leaks stack traces to the client.
"""

import logging
import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_required_user, hash_password
from app.core.plans import apply_plan_limits, PLAN_LIMITS, PLAN_MONTHLY_PRICE
from app.models.user import User
from app.models.scan import Scan
from app.models.target import Target

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Admin guard ──────────────────────────────────────────────────────────────

async def require_admin(user: User = Depends(get_required_user)) -> User:
    if getattr(user, "role", "user") != "admin":
        raise HTTPException(403, "Admin toegang vereist")
    return user


# ── Helpers ──────────────────────────────────────────────────────────────────

def _iso(value) -> str | None:
    if value is None:
        return None
    try:
        return value.isoformat()
    except Exception:
        return None


def _user_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "company_name": user.company_name,
        "plan": user.plan,
        "plan_interval": user.plan_interval,
        "plan_expires_at": _iso(user.plan_expires_at),
        "max_targets": user.max_targets,
        "max_scans_per_month": user.max_scans_per_month,
        "scans_this_month": user.scans_this_month,
        "credits_remaining": getattr(user, "credits_remaining", 0),
        "credits_total": getattr(user, "credits_total", 0),
        "is_active": user.is_active,
        "role": user.role,
        "created_at": _iso(user.created_at),
        "last_login_at": _iso(user.last_login_at),
    }


def _parse_iso(value) -> datetime | None:
    """Parse an ISO-8601 string into a datetime, or None on any failure."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except Exception:
        return None


async def _get_user_or_404(db: AsyncSession, user_id: str) -> User:
    try:
        uid = uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        raise HTTPException(404, "Gebruiker niet gevonden")
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "Gebruiker niet gevonden")
    return user


def _start_of_today_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_month_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


# ── Pydantic bodies ──────────────────────────────────────────────────────────

class CreateUserBody(BaseModel):
    email: str
    name: str
    company_name: str | None = None
    plan: str
    password: str
    interval: str | None = None
    send_welcome_email: bool = False


class PatchUserBody(BaseModel):
    plan: str | None = None
    max_targets: int | None = None
    max_scans_per_month: int | None = None
    custom_modules: bool | None = None
    scheduled_scans: bool | None = None
    white_label: bool | None = None
    ai_upgrade: str | None = None
    is_active: bool | None = None
    role: str | None = None
    plan_expires_at: str | None = None
    plan_interval: str | None = None


class AddCreditsBody(BaseModel):
    credits: int
    reason: str | None = None


class InitBody(BaseModel):
    email: str
    password: str
    secret: str


# ── User listing & detail ────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    search: str | None = None,
    plan: str | None = None,
    sort: str = "created_at",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        query = select(User)
        if search:
            pattern = f"%{search}%"
            query = query.where(or_(User.email.ilike(pattern), User.name.ilike(pattern)))
        if plan:
            query = query.where(User.plan == plan)

        if sort == "plan":
            query = query.order_by(User.plan.asc(), User.created_at.desc())
        elif sort == "scans":
            query = query.order_by(User.scans_this_month.desc())
        else:
            query = query.order_by(User.created_at.desc())

        result = await db.execute(query)
        users = result.scalars().all()
        return [_user_dict(u) for u in users]
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.list_users failed")
        raise HTTPException(500, "Kon gebruikers niet ophalen")


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await _get_user_or_404(db, user_id)

        scans_res = await db.execute(
            select(Scan).where(Scan.user_id == user.id).order_by(Scan.created_at.desc())
        )
        scans = scans_res.scalars().all()

        targets_res = await db.execute(select(Target).where(Target.user_id == user.id))
        targets = targets_res.scalars().all()

        data = _user_dict(user)
        data["scans"] = [
            {
                "id": str(s.id),
                "target_id": str(s.target_id) if s.target_id else None,
                "security_score": s.security_score,
                "critical_count": s.critical_count,
                "status": s.status,
                "created_at": _iso(s.created_at),
            }
            for s in scans
        ]
        data["targets"] = [{"id": str(t.id), "value": t.value} for t in targets]
        return data
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.get_user failed")
        raise HTTPException(500, "Kon gebruiker niet ophalen")


# ── User creation ────────────────────────────────────────────────────────────

@router.post("/users")
async def create_user(
    body: CreateUserBody,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        existing = await db.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(400, "E-mailadres is al in gebruik")

        now = datetime.now(timezone.utc)
        user = User(
            email=body.email,
            name=body.name,
            company_name=body.company_name,
            full_name=body.name,
            password_hash=hash_password(body.password),
            clerk_id=f"local-admin-{uuid.uuid4()}",
            api_key=secrets.token_hex(32),
            is_active=True,
            role="user",
            terms_accepted=True,
            onboarding_completed=True,
        )
        apply_plan_limits(user, body.plan)
        user.plan_interval = body.interval
        user.plan_started_at = now

        db.add(user)
        await db.commit()
        await db.refresh(user)

        if body.send_welcome_email:
            try:
                from app.services.email import send_welcome_email
                send_welcome_email(user, body.plan, body.interval)
            except Exception:
                logger.warning("admin.create_user welcome email failed", exc_info=True)

        return _user_dict(user)
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.create_user failed")
        await db.rollback()
        raise HTTPException(500, "Kon gebruiker niet aanmaken")


# ── User update ──────────────────────────────────────────────────────────────

@router.patch("/users/{user_id}")
async def patch_user(
    user_id: str,
    body: PatchUserBody,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await _get_user_or_404(db, user_id)
        data = body.model_dump(exclude_unset=True)

        # Plan first (sets the defaults), then explicit overrides on top.
        if "plan" in data and data["plan"] is not None:
            apply_plan_limits(user, data["plan"])

        for field in (
            "max_targets",
            "max_scans_per_month",
            "custom_modules",
            "scheduled_scans",
            "white_label",
            "ai_upgrade",
            "is_active",
            "role",
            "plan_interval",
        ):
            if field in data and data[field] is not None:
                setattr(user, field, data[field])

        if "plan_expires_at" in data:
            user.plan_expires_at = _parse_iso(data["plan_expires_at"])

        await db.commit()
        await db.refresh(user)
        return _user_dict(user)
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.patch_user failed")
        await db.rollback()
        raise HTTPException(500, "Kon gebruiker niet bijwerken")


# ── Deletion ─────────────────────────────────────────────────────────────────

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await _get_user_or_404(db, user_id)
        user.is_active = False
        await db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.delete_user failed")
        await db.rollback()
        raise HTTPException(500, "Kon gebruiker niet verwijderen")


@router.delete("/users/{user_id}/hard")
async def hard_delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await _get_user_or_404(db, user_id)
        await db.delete(user)
        await db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.hard_delete_user failed")
        await db.rollback()
        raise HTTPException(500, "Kon gebruiker niet verwijderen")


# ── Credits (manual grant for support / compensation / test accounts) ─────────

@router.post("/users/{user_id}/add-credits")
async def admin_add_credits(
    user_id: str,
    body: AddCreditsBody,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.credits <= 0:
        raise HTTPException(400, "Aantal credits moet groter zijn dan 0")

    user = await _get_user_or_404(db, user_id)

    import secrets as _secrets
    from app.services.credits import credits_service

    # stripe_payment_id is unique → suffix a token so repeated grants don't clash.
    await credits_service.add_credits(
        db,
        user_id=user.id,
        amount=body.credits,
        package_name="admin",
        price_paid=0,
        stripe_payment_id=f"admin_manual_{_secrets.token_hex(8)}",
    )
    await db.refresh(user)
    logger.info(
        "admin %s granted %d credits to %s (reason=%s)",
        admin.email, body.credits, user.email, (body.reason or "-"),
    )
    return _user_dict(user)


# ── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        total_users = await db.scalar(select(func.count(User.id))) or 0
        active_subscriptions = await db.scalar(
            select(func.count(User.id)).where(User.plan.notin_(["trial"]))
        ) or 0
        trial_users = await db.scalar(
            select(func.count(User.id)).where(User.plan == "trial")
        ) or 0

        today = _start_of_today_utc()
        month = _start_of_month_utc()
        total_scans_today = await db.scalar(
            select(func.count(Scan.id)).where(Scan.created_at >= today)
        ) or 0
        total_scans_this_month = await db.scalar(
            select(func.count(Scan.id)).where(Scan.created_at >= month)
        ) or 0

        # Revenue estimate — sum of monthly price over non-trial users.
        plan_counts_res = await db.execute(
            select(User.plan, func.count(User.id)).group_by(User.plan)
        )
        plan_counts = {plan: count for plan, count in plan_counts_res.all()}

        monthly_revenue = 0
        for plan, count in plan_counts.items():
            if plan == "trial":
                continue
            monthly_revenue += PLAN_MONTHLY_PRICE.get(plan, 0) * count

        plans_breakdown = {
            "trial": plan_counts.get("trial", 0),
            "credits": plan_counts.get("credits", 0),
            "starter": plan_counts.get("starter", 0),
            "business": plan_counts.get("business", 0),
            "enterprise": plan_counts.get("enterprise", 0),
            "admin": plan_counts.get("admin", 0),
        }

        # ── Credits metrics ──
        from datetime import timedelta
        from app.models.credits import ScanCredit, CreditUsage

        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        # Sold = paid purchases only (exclude trial/admin grants where price_paid == 0).
        total_credits_sold = await db.scalar(
            select(func.coalesce(func.sum(ScanCredit.credits_purchased), 0)).where(
                ScanCredit.price_paid > 0
            )
        ) or 0
        total_credits_used = await db.scalar(
            select(func.coalesce(func.sum(CreditUsage.credits_used), 0))
        ) or 0
        # Total credits revenue (all time), in eurocents.
        credits_revenue_cents = await db.scalar(
            select(func.coalesce(func.sum(ScanCredit.price_paid), 0))
        ) or 0
        credits_revenue_30d_cents = await db.scalar(
            select(func.coalesce(func.sum(ScanCredit.price_paid), 0)).where(
                ScanCredit.created_at >= thirty_days_ago
            )
        ) or 0
        # Credits still held by non-unlimited users (excludes business/enterprise).
        credits_in_circulation = await db.scalar(
            select(func.coalesce(func.sum(User.credits_remaining), 0)).where(
                User.plan.notin_(("business", "enterprise"))
            )
        ) or 0

        # ── Operational metrics (Blok 5) ──
        from app.models.agent import ScanixAgent
        from app.models.project import ScanProject

        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        online_cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)

        active_agents = await db.scalar(
            select(func.count(ScanixAgent.id)).where(ScanixAgent.last_seen >= online_cutoff)
        ) or 0
        total_projects = await db.scalar(select(func.count(ScanProject.id))) or 0
        scans_this_week = await db.scalar(
            select(func.count(Scan.id)).where(Scan.created_at >= week_ago)
        ) or 0
        avg_duration_s = await db.scalar(
            select(func.avg(func.extract("epoch", Scan.completed_at - Scan.started_at))).where(
                Scan.completed_at.isnot(None), Scan.started_at.isnot(None)
            )
        )
        avg_scan_duration_min = round(float(avg_duration_s) / 60, 1) if avg_duration_s else 0

        # Scans per day, last 14 days (grouped, then filled into a dense array).
        fourteen_ago = datetime.now(timezone.utc) - timedelta(days=13)
        per_day_res = await db.execute(
            select(func.date_trunc("day", Scan.created_at).label("d"), func.count(Scan.id))
            .where(Scan.created_at >= fourteen_ago)
            .group_by("d")
        )
        per_day_map = {row[0].date().isoformat(): int(row[1]) for row in per_day_res.all() if row[0]}
        scans_per_day = []
        for i in range(13, -1, -1):
            day = (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat()
            scans_per_day.append({"date": day, "count": per_day_map.get(day, 0)})

        # Top findings across recent completed scans (best-effort, in Python).
        top_res = await db.execute(
            select(Scan.findings).where(Scan.status == "completed", Scan.findings.isnot(None)).limit(300)
        )
        tally: dict[str, dict] = {}
        for (findings,) in top_res.all():
            for f in (findings or []):
                title = str((f or {}).get("title") or (f or {}).get("name") or "Onbekend")[:120]
                sev = str((f or {}).get("severity", "info")).lower()
                entry = tally.setdefault(title, {"title": title, "count": 0, "severity": sev})
                entry["count"] += 1
        top_findings = sorted(tally.values(), key=lambda x: x["count"], reverse=True)[:5]

        return {
            "total_users": total_users,
            "active_subscriptions": active_subscriptions,
            "trial_users": trial_users,
            "total_scans_today": total_scans_today,
            "scans_today": total_scans_today,
            "scans_this_week": int(scans_this_week),
            "total_scans_this_month": total_scans_this_month,
            "active_agents": int(active_agents),
            "total_projects": int(total_projects),
            "avg_scan_duration": avg_scan_duration_min,
            "scans_per_day": scans_per_day,
            "top_findings": top_findings,
            "revenue_estimate": {
                "monthly": monthly_revenue,
                "yearly": monthly_revenue * 12,
            },
            "plans_breakdown": plans_breakdown,
            "credits": {
                "total_sold": int(total_credits_sold),
                "total_used": int(total_credits_used),
                "revenue_eur": round(int(credits_revenue_cents) / 100, 2),
                "revenue_30d_eur": round(int(credits_revenue_30d_cents) / 100, 2),
                "in_circulation": int(credits_in_circulation),
            },
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.get_stats failed")
        raise HTTPException(500, "Kon statistieken niet ophalen")


# ── All scans (admin-wide) ────────────────────────────────────────────────────
@router.get("/scans")
async def admin_list_scans(
    status: str | None = None,
    user_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Every scan across all users, with filters."""
    from app.models.target import Target

    query = select(Scan)
    if status and status != "all":
        query = query.where(Scan.status == status)
    if user_id:
        try:
            query = query.where(Scan.user_id == uuid.UUID(user_id))
        except (ValueError, TypeError):
            pass
    if date_from:
        try:
            query = query.where(Scan.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.where(Scan.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    query = query.order_by(Scan.created_at.desc()).limit(min(limit, 200)).offset(offset)
    rows = (await db.execute(query)).scalars().all()

    # Hydrate user emails + target values in bulk.
    user_ids = {s.user_id for s in rows}
    target_ids = {s.target_id for s in rows}
    umap = {}
    tmap = {}
    if user_ids:
        ures = await db.execute(select(User.id, User.email).where(User.id.in_(user_ids)))
        umap = {uid: email for uid, email in ures.all()}
    if target_ids:
        tres = await db.execute(select(Target.id, Target.value).where(Target.id.in_(target_ids)))
        tmap = {tid: val for tid, val in tres.all()}

    def _duration(s: Scan) -> int | None:
        if s.started_at and s.completed_at:
            return int((s.completed_at - s.started_at).total_seconds())
        return None

    return [
        {
            "scan_id": str(s.id),
            "user_email": umap.get(s.user_id),
            "target": tmap.get(s.target_id),
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "duration_s": _duration(s),
            "findings_count": len(s.findings or []),
        }
        for s in rows
    ]


# ── All agents (admin-wide) ───────────────────────────────────────────────────
@router.get("/agents")
async def admin_list_agents(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.agent import ScanixAgent

    online_cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
    rows = (await db.execute(select(ScanixAgent).order_by(ScanixAgent.created_at.desc()))).scalars().all()
    user_ids = {a.user_id for a in rows}
    umap = {}
    if user_ids:
        ures = await db.execute(select(User.id, User.email).where(User.id.in_(user_ids)))
        umap = {uid: email for uid, email in ures.all()}

    def _online(a) -> bool:
        if not a.last_seen:
            return False
        last = a.last_seen if a.last_seen.tzinfo else a.last_seen.replace(tzinfo=timezone.utc)
        return last >= online_cutoff

    return [
        {
            "agent_id": str(a.id),
            "user_email": umap.get(a.user_id),
            "name": a.name,
            "status": "online" if _online(a) else "offline",
            "hostname": a.hostname,
            "local_ip": a.local_ip,
            "last_seen": a.last_seen.isoformat() if a.last_seen else None,
        }
        for a in rows
    ]


# ── Password reset & suspend / activate ──────────────────────────────────────

@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await _get_user_or_404(db, user_id)
        temp_password = secrets.token_urlsafe(9)
        user.password_hash = hash_password(temp_password)
        await db.commit()

        try:
            from app.services.email import send_password_reset_email
            send_password_reset_email(user, temp_password)
        except Exception:
            logger.warning("admin.reset_password email failed", exc_info=True)

        return {"temp_password": temp_password}
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.reset_password failed")
        await db.rollback()
        raise HTTPException(500, "Kon wachtwoord niet resetten")


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await _get_user_or_404(db, user_id)
        user.is_active = False
        await db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.suspend_user failed")
        await db.rollback()
        raise HTTPException(500, "Kon gebruiker niet schorsen")


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await _get_user_or_404(db, user_id)
        user.is_active = True
        await db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.activate_user failed")
        await db.rollback()
        raise HTTPException(500, "Kon gebruiker niet activeren")


# ── Bootstrap first admin (no auth) ──────────────────────────────────────────

@router.post("/init")
async def init_admin(
    body: InitBody,
    db: AsyncSession = Depends(get_db),
):
    try:
        admin_count = await db.scalar(
            select(func.count(User.id)).where(User.role == "admin")
        ) or 0
        if admin_count > 0:
            raise HTTPException(403, "Admin bestaat al")

        if body.secret != os.getenv("ADMIN_INIT_SECRET", "scanix-admin-init"):
            raise HTTPException(403, "Ongeldige geheime sleutel")

        now = datetime.now(timezone.utc)
        user = User(
            email=body.email,
            name="Admin",
            full_name="Admin",
            password_hash=hash_password(body.password),
            clerk_id=f"local-admin-{uuid.uuid4()}",
            api_key=secrets.token_hex(32),
            is_active=True,
            role="admin",
            terms_accepted=True,
            onboarding_completed=True,
        )
        apply_plan_limits(user, "admin")
        user.plan_started_at = now

        db.add(user)
        await db.commit()
        return {"ok": True, "email": body.email}
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.init_admin failed")
        await db.rollback()
        raise HTTPException(500, "Kon admin niet aanmaken")


# ── Test account seed (no JWT; gated by the admin-init secret header) ─────────

@router.post("/create-test-account")
async def create_test_account(
    x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret"),
    db: AsyncSession = Depends(get_db),
):
    """Create or reset the ready-to-test account (test@scanix.nl). Idempotent."""
    if x_admin_secret != os.getenv("ADMIN_INIT_SECRET", "scanix-admin-init"):
        raise HTTPException(403, "Ongeldige geheime sleutel")
    try:
        from app.services.seed import create_or_reset_test_account
        info = await create_or_reset_test_account(db)
        return {"ok": True, **info}
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin.create_test_account failed")
        await db.rollback()
        raise HTTPException(500, "Kon testaccount niet aanmaken")
