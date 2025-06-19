from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from .base import ORMBaseModel

if TYPE_CHECKING:
    from .pass_schema import Pass
    from .school_schema import School


class LocationBase(ORMBaseModel):
    school_id: UUID
    name: str
    description: Optional[str] = None
    default_duration: Optional[int] = 10  # minutes
    requires_approval: Optional[bool] = True
    is_active: Optional[bool] = True
    # Special types
    is_early_release_only: Optional[bool] = False
    is_summons_only: Optional[bool] = False
    room_number: Optional[str] = None


class LocationCreate(LocationBase):
    pass


class LocationUpdate(LocationBase):
    pass


class Location(LocationBase):
    id: UUID
    created_at: Optional[datetime] = None

    # Relationships
    school: "School"
    passes: List["Pass"] = [] 