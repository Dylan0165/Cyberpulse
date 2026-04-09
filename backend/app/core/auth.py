"""Clerk JWT verification and user extraction middleware."""

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx

from app.core.config import get_settings

security = HTTPBearer()
settings = get_settings()

_clerk_jwks_cache: dict | None = None


async def _get_clerk_jwks() -> dict:
    """Fetch Clerk JWKS for JWT verification."""
    global _clerk_jwks_cache
    if _clerk_jwks_cache:
        return _clerk_jwks_cache

    async with httpx.AsyncClient() as client:
        # Clerk exposes JWKS at a well-known endpoint
        resp = await client.get(
            "https://api.clerk.dev/v1/jwks",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        )
        resp.raise_for_status()
        _clerk_jwks_cache = resp.json()
        return _clerk_jwks_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validate Clerk JWT and return user claims."""
    token = credentials.credentials
    try:
        jwks = await _get_clerk_jwks()
        # Decode header to find the right key
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

        if not rsa_key:
            raise HTTPException(status_code=401, detail="Invalid token key")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")

        return {
            "clerk_id": user_id,
            "email": payload.get("email", ""),
            "metadata": payload.get("public_metadata", {}),
        }

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")


async def get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
