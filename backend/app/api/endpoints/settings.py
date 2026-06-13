"""Settings endpoints — Kali VM scanner configuration and connectivity test."""

import time

import httpx
from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.auth import get_current_user

router = APIRouter()

settings = get_settings()


@router.get("/settings/kali")
async def get_kali_settings(
    current_user: dict = Depends(get_current_user),
):
    return {
        "host": settings.kali_vm_host,
        "port": settings.kali_vm_port,
    }


@router.post("/settings/kali/test")
async def test_kali_connection(
    current_user: dict = Depends(get_current_user),
):
    url = f"http://{settings.kali_vm_host}:{settings.kali_vm_port}/health"
    headers = {"x-api-key": settings.scanner_api_key}
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url, headers=headers)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "connected": response.status_code < 400,
            "response_time_ms": elapsed_ms,
        }
    except Exception:
        return {"connected": False, "response_time_ms": 0}
