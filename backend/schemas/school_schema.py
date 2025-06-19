from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from .base import ORMBaseModel

if TYPE_CHECKING:
    from .location_schema import Location
    from .profile_schema import Profile


class SchoolBase(ORMBaseModel):
    name: str
    default_pass_duration: Optional[int] = None  # minutes
    concurrent_pass_limit: Optional[int] = None  # max concurrent passes
    pre_approved_settings: Optional[Dict[str, Any]] = None


class SchoolCreate(SchoolBase):
    """Fields required when creating a school."""
    pass


class SchoolUpdate(SchoolBase):
    """Fields allowed when updating a school."""
    pass


class School(SchoolBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Relationships
    locations: List["Location"] = []
    profiles: List["Profile"] = [] 