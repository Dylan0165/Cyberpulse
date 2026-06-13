"""Permissive authentication.

- get_current_user: legacy permissive dependency (always returns a mock dict)
  kept so existing endpoints keep working unchanged.
- get_optional_user: returns the real User from a JWT (Bearer header or
  cp_token cookie) if present and valid, else None — never raises 401.
- get_required_user: like optional but raises 401 when no valid user.

JWT via python-jose (HS256). Passwords via passlib bcrypt.
School/commercial project: unauthenticated requests are allowed (demo mode).
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.core.database import get_db
from app.models.user import User

JWT_SECRET = os.getenv("JWT_SECRET", "cyberpulse-dev-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7

_MOCK_USER = {
    "id": "student",
    "clerk_id": "student",
    "email": "student@cyberpulse.local",
    "role": "admin",
    "metadata": {},
}


# ── Password hashing ────────────────────────────────────────────────────────
# Use the `bcrypt` library directly. passlib 1.7.4 + bcrypt 4.x is a well-known
# source of runtime errors (reads removed bcrypt.__about__), so we avoid passlib.
# bcrypt has a hard 72-byte input limit — truncate before hashing/verifying.

def hash_password(password: str) -> str:
    import bcrypt
    pw = (password or "").encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        import bcrypt
        pw = (password or "").encode("utf-8")[:72]
        return bcrypt.checkpw(pw, (password_hash or "").encode("utf-8"))
    except Exception:
        return False


# ── JWT ─────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def _extract_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    cookie = request.cookies.get("cp_token")
    if cookie:
        return cookie
    return None


# ── Dependencies ──────────────────────────────────────────────────────────────

async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Return the authenticated User, or None. Never raises 401 (demo mode)."""
    token = _extract_token(request)
    if not token:
        return None
    payload = _decode_token(token)
    if not payload:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        uid = uuid.UUID(str(sub))
    except (ValueError, TypeError):
        return None
    try:
        result = await db.execute(select(User).where(User.id == uid))
        return result.scalar_one_or_none()
    except Exception:
        return None


async def get_required_user(
    user: Optional[User] = Depends(get_optional_user),
) -> User:
    """Require a valid authenticated user — raises 401 otherwise."""
    if user is None:
        raise HTTPException(status_code=401, detail="Niet ingelogd")
    return user


# ── Legacy permissive dependency (kept for existing endpoints) ──────────────

async def get_current_user() -> dict:
    return _MOCK_USER


async def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
