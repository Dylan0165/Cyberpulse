"""Pydantic schemas for target management."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator
import re
import ipaddress


class TargetScope(BaseModel):
    ports: list[int] = []
    paths: list[str] = []
    exclude_ips: list[str] = []


class TargetCreate(BaseModel):
    name: str
    target_type: str  # domain, ip, ip_range, url
    value: str
    scope: TargetScope | None = None

    @field_validator("target_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"domain", "ip", "ip_range", "url"}
        if v not in allowed:
            raise ValueError(f"target_type must be one of: {allowed}")
        return v

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str, info) -> str:
        v = v.strip().lower()
        # Basic validation — detailed validation happens per type
        if not v:
            raise ValueError("Target value cannot be empty")
        if len(v) > 500:
            raise ValueError("Target value too long")
        return v


class TargetResponse(BaseModel):
    id: UUID
    name: str
    target_type: str
    value: str
    scope: dict | None
    is_verified: bool
    verified_at: datetime | None
    verification_method: str | None
    verification_token: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VerifyDNSRequest(BaseModel):
    target_id: UUID


class VerifyFileRequest(BaseModel):
    target_id: UUID


class VerifyIPDeclarationRequest(BaseModel):
    target_id: UUID
    legal_declaration: bool  # Must be True

    @field_validator("legal_declaration")
    @classmethod
    def must_accept(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must confirm legal ownership of this IP range")
        return v
