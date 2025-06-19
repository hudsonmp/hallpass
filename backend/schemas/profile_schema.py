from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic import EmailStr

from .base import ORMBaseModel
from .enums import RoleEnum

if TYPE_CHECKING:
    from .pass_schema import Pass
    from .school_schema import School


class ProfileBase(ORMBaseModel):
    school_id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: RoleEnum
    # Student fields
    student_id: Optional[str] = None
    grade_level: Optional[int] = None
    # Teacher fields
    teacher_id: Optional[str] = None
    department: Optional[str] = None
    # Admin fields
    admin_permissions: Optional[List[str]] = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class Profile(ProfileBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Relationships
    school: "School"
    passes: List["Pass"] = [] 