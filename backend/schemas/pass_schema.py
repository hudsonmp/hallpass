from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from .base import ORMBaseModel
from .enums import PassStatusEnum

if TYPE_CHECKING:
    from .location_schema import Location
    from .profile_schema import Profile


class PassBase(ORMBaseModel):
    school_id: UUID
    student_id: UUID
    location_id: UUID

    status: Optional[PassStatusEnum] = PassStatusEnum.pending

    requested_start_time: Optional[datetime] = None
    requested_end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None

    # Flags
    is_summons: Optional[bool] = False
    is_early_release: Optional[bool] = False

    student_reason: Optional[str] = None


class PassCreate(PassBase):
    """Schema used by students when requesting a pass."""
    pass


class PassApprove(ORMBaseModel):
    approver_id: UUID
    approval_notes: Optional[str] = None
    approved_at: Optional[datetime] = None  # Server will usually set this
    status: PassStatusEnum = PassStatusEnum.approved


class PassComplete(ORMBaseModel):
    status: PassStatusEnum = PassStatusEnum.completed


class Pass(PassBase):
    id: UUID
    approver_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    verification_code: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Relationships
    student: "Profile"
    location: "Location"
    approver: Optional["Profile"] = None 