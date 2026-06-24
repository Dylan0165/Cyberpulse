"""Scanix Agent endpoints.

Two auth styles:
  * Dashboard endpoints use the normal JWT user (get_required_user).
  * Agent endpoints (heartbeat, scan-result) authenticate with the agent's
    secret token in the X-Agent-Token header.

Agents poll /heartbeat; any scan created for that agent (config.agent_id) and
still 'pending' is handed back as a pending_scan. The agent runs it locally and
streams output to /scan-result, which republishes onto the same Redis live
channel the cloud worker uses, so the live terminal works unchanged.
"""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_required_user
from app.core.config import get_settings
from app.core.redis import get_redis
from app.models.user import User
from app.models.agent import ScanixAgent
from app.models.scan import Scan
from app.models.target import Target
from app.services.credits import credits_service

settings = get_settings()
router = APIRouter(prefix="/agents", tags=["agents"])

ONLINE_WINDOW_S = 60  # last_seen within this many seconds == online


# ── Agent-token auth ──────────────────────────────────────────────────────────
async def get_agent(
    x_agent_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> ScanixAgent:
    if not x_agent_token:
        raise HTTPException(status_code=401, detail="Missing X-Agent-Token")
    result = await db.execute(select(ScanixAgent).where(ScanixAgent.agent_token == x_agent_token))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid agent token")
    return agent


def _is_online(agent: ScanixAgent) -> bool:
    if not agent.last_seen:
        return False
    last = agent.last_seen
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last).total_seconds() < ONLINE_WINDOW_S


def _agent_dict(agent: ScanixAgent) -> dict:
    online = _is_online(agent)
    return {
        "agent_id": str(agent.id),
        "name": agent.name,
        "status": "online" if online else "offline",
        "os": agent.os,
        "hostname": agent.hostname,
        "local_ip": agent.local_ip,
        "version": agent.version,
        "last_seen": agent.last_seen.isoformat() if agent.last_seen else None,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }


# ── Request models ──────────────────────────────────────────────────────────
class RegisterAgentRequest(BaseModel):
    name: str


class HeartbeatRequest(BaseModel):
    hostname: str | None = None
    local_ip: str | None = None
    os: str | None = None
    version: str | None = None


class ScanResultRequest(BaseModel):
    scan_id: str
    event: str            # output | completed | error
    data: dict = {}


class AgentScanRequest(BaseModel):
    target: str


# ── Dashboard (JWT) endpoints ─────────────────────────────────────────────────
@router.post("/register")
async def register_agent(
    body: RegisterAgentRequest,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    token = secrets.token_urlsafe(32)
    agent = ScanixAgent(user_id=user.id, name=body.name.strip() or "Agent", agent_token=token)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    base = settings.frontend_url.replace("3000", "8000") if "localhost" in settings.frontend_url else "https://app.scanix.nl"
    return {
        "agent_id": str(agent.id),
        "agent_token": token,
        "install_command": f"curl -sSL {base}/agent/install.sh | AGENT_TOKEN={token} bash",
    }


@router.get("")
@router.get("/")
async def list_agents(
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScanixAgent).where(ScanixAgent.user_id == user.id).order_by(ScanixAgent.created_at.desc())
    )
    return [_agent_dict(a) for a in result.scalars().all()]


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: uuid.UUID,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScanixAgent).where(ScanixAgent.id == agent_id, ScanixAgent.user_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent niet gevonden")
    await db.delete(agent)
    await db.commit()
    return {"deleted": True}


@router.post("/{agent_id}/scan")
async def start_agent_scan(
    agent_id: uuid.UUID,
    body: AgentScanRequest,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue a scan for the agent to pick up on its next heartbeat."""
    result = await db.execute(
        select(ScanixAgent).where(ScanixAgent.id == agent_id, ScanixAgent.user_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent niet gevonden")
    if not _is_online(agent):
        raise HTTPException(status_code=409, detail={
            "error": "agent_offline",
            "message": "Deze agent is offline. Start de agent op uw server en probeer opnieuw.",
        })

    target = Target(
        user_id=user.id, name=body.target, target_type="single", value=body.target, is_verified=True
    )
    db.add(target)
    await db.flush()

    scan = Scan(
        user_id=user.id,
        target_id=target.id,
        scan_type="quick",
        phases=["recon", "vulnerability", "ssl"],
        config={"scan_mode": "safe", "target_type": "single", "agent_id": str(agent.id)},
        save_report=True,
        status="pending",
    )
    db.add(scan)
    await db.flush()
    # 1 credit per agent scan (atomic; raises 402 if empty).
    await credits_service.deduct_credit(db, user.id, scan.id)
    await db.commit()
    await db.refresh(scan)
    return {"scan_id": str(scan.id), "message": "Scan gepland voor agent"}


# ── Agent-token endpoints ─────────────────────────────────────────────────────
@router.post("/heartbeat")
async def heartbeat(
    body: HeartbeatRequest,
    agent: ScanixAgent = Depends(get_agent),
    db: AsyncSession = Depends(get_db),
):
    agent.hostname = body.hostname or agent.hostname
    agent.local_ip = body.local_ip or agent.local_ip
    agent.os = body.os or agent.os
    agent.version = body.version or agent.version
    agent.last_seen = datetime.now(timezone.utc)
    if agent.status == "offline":
        agent.status = "online"

    # Hand back pending scans assigned to this agent.
    res = await db.execute(
        select(Scan).where(Scan.user_id == agent.user_id, Scan.status == "pending")
    )
    pending = []
    for s in res.scalars().all():
        if (s.config or {}).get("agent_id") == str(agent.id):
            tres = await db.execute(select(Target).where(Target.id == s.target_id))
            tgt = tres.scalar_one_or_none()
            s.status = "running"  # claim it so it isn't handed out twice
            pending.append({"scan_id": str(s.id), "target": tgt.value if tgt else None, "phases": s.phases})
    await db.commit()
    return {"status": "ok", "pending_scans": pending}


@router.post("/scan-result")
async def scan_result(
    body: ScanResultRequest,
    agent: ScanixAgent = Depends(get_agent),
    db: AsyncSession = Depends(get_db),
):
    # Verify the scan belongs to this agent's owner.
    try:
        sid = uuid.UUID(body.scan_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Bad scan_id")

    res = await db.execute(select(Scan).where(Scan.id == sid, Scan.user_id == agent.user_id))
    scan = res.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan niet gevonden")

    redis = await get_redis()

    async def _pub(event: dict) -> None:
        payload = json.dumps(event)
        await redis.publish(f"scan:{body.scan_id}:live", payload)
        await redis.rpush(f"scan:{body.scan_id}:log", payload)
        await redis.expire(f"scan:{body.scan_id}:log", 86400)

    if body.event == "output":
        await _pub({
            "type": "tool_output",
            "phase": body.data.get("phase", "Agent"),
            "output": body.data.get("output", ""),
            "source": "agent",
        })
    elif body.event == "completed":
        scan.status = "completed"
        agent.status = "online"
        await _pub({"type": "scan_complete", "source": "agent"})
        await db.commit()
    elif body.event == "error":
        scan.status = "failed"
        await _pub({"type": "error", "message": body.data.get("output", "agent error")})
        await db.commit()

    return {"status": "ok"}
