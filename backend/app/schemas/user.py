"""Pydantic schemas for user accounts."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: UUID
    clerk_id: str
    email: str
    full_name: str | None
    company: str | None
    plan: str
    credits: int
    max_concurrent_scans: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
