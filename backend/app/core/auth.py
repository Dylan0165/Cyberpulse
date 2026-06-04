"""Auth bypass — school project on closed netlab, no public access."""

from fastapi import Request

_MOCK_USER = {
    "id": "student",
    "clerk_id": "student",
    "email": "student@cyberpulse.local",
    "role": "admin",
    "metadata": {},
}


async def get_current_user() -> dict:
    return _MOCK_USER


async def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
