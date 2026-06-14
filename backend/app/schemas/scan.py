"""Pydantic schemas for scan management."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator


VALID_PHASES = {
    # Kali VM phases
    "recon", "vulnerability", "webapp", "network", "auth", "ssl", "cloud", "osint",
    # Custom CyberPulse modules
    "m09", "m10", "m11", "m12", "m13", "m14", "m15", "m16", "m17",
}
VALID_SCAN_TYPES = {"quick", "full", "custom"}

QUICK_PHASES = ["recon", "vulnerability", "ssl"]
FULL_PHASES = ["recon", "vulnerability", "webapp", "network", "auth", "ssl", "osint"]


class ScanCreate(BaseModel):
    target_id: UUID
    scan_type: str = "quick"
    phases: list[str] = []
    save_report: bool = True
    config: dict = {}
    # Scan context — stored inside config JSONB, no extra DB column needed
    scan_mode: str = "blackbox"    # blackbox | graybox | whitebox
    target_type: str = "web"       # web | api | network | windows | linux
    credentials: dict = {}         # username, password, ssh_key, bearer_token, custom_headers

    @field_validator("scan_type")
    @classmethod
    def validate_scan_type(cls, v: str) -> str:
        if v not in VALID_SCAN_TYPES:
            raise ValueError(f"scan_type must be one of: {VALID_SCAN_TYPES}")
        return v

    @field_validator("phases")
    @classmethod
    def validate_phases(cls, v: list[str]) -> list[str]:
        for p in v:
            if p not in VALID_PHASES:
                raise ValueError(f"Invalid phase: {p}. Valid: {VALID_PHASES}")
        return v


class ScanResponse(BaseModel):
    id: UUID
    target_id: UUID
    target_value: str | None = None   # resolved IP/hostname for display
    scan_mode: str | None = None
    scan_type: str
    phases: list[str]
    status: str
    current_phase: str | None
    progress: int
    save_report: bool
    security_score: float | None
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    credits_used: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    share_token: str | None

    model_config = {"from_attributes": True}


class ScanDetailResponse(ScanResponse):
    # Detail-only: the full per-phase/per-tool output so the scan-detail
    # terminal can be rebuilt for historical scans. Kept OUT of the list
    # response (ScanResponse) so listing stays lean.
    tool_outputs: dict | None = None
    phases_completed: list | None = None


class ScanListResponse(BaseModel):
    scans: list[ScanResponse]
    total: int
    page: int
    page_size: int


class ScanReportResponse(BaseModel):
    scan_id: UUID
    report_data: dict | None
    security_score: float | None
    generated_at: datetime | None

    model_config = {"from_attributes": True}
