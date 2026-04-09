"""Pydantic schemas for NDA acceptance and audit logs."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator


class NDAAcceptRequest(BaseModel):
    target_id: UUID
    scan_id: UUID
    authorization_confirmed: bool
    nda_accepted: bool

    @field_validator("authorization_confirmed")
    @classmethod
    def must_confirm_auth(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must confirm you are authorized to test this target")
        return v

    @field_validator("nda_accepted")
    @classmethod
    def must_accept_nda(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the NDA and Rules of Engagement")
        return v


class NDAAcceptResponse(BaseModel):
    id: UUID
    user_id: UUID
    target_id: UUID
    authorization_confirmed: bool
    nda_accepted: bool
    nda_version: str
    roe_version: str
    accepted_at: datetime

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: UUID
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict | None
    ip_address: str
    timestamp: datetime

    model_config = {"from_attributes": True}
