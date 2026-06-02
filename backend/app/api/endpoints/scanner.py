"""Scanner connectivity endpoints."""

from fastapi import APIRouter

from app.services.scanner import check_kali_connectivity

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/health")
def scanner_health():
    """Check if the Kali VM scanner API is reachable and return available tools."""
    return check_kali_connectivity()
