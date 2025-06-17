from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

class PassCreateRequest(BaseModel):
    location_id: uuid.UUID
    student_reason: Optional[str] = None
    requested_start_time: Optional[datetime] = None
    is_summons: bool = False
    is_early_release: bool = False

class PassResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    location_id: uuid.UUID
    school_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    status: str
    
    # Student information
    student_name: str
    student_reason: Optional[str]
    
    # Location information
    location_name: str
    location_description: Optional[str]
    
    # Timing information
    requested_start_time: Optional[datetime]
    actual_start_time: Optional[datetime]
    requested_end_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    duration_minutes: Optional[int]
    
    # Approval information
    approver_id: Optional[uuid.UUID]
    approver_name: Optional[str]
    approved_at: Optional[datetime]
    approval_notes: Optional[str]
    
    # Special pass types
    is_summons: bool
    is_early_release: bool
    
    # QR code for verification
    verification_code: Optional[str]
    
    # Administrative notes
    admin_notes: Optional[str]

class PassListResponse(BaseModel):
    passes: List[PassResponse]
    total: int

class PassStatusUpdate(BaseModel):
    status: str = Field(..., regex="^(approved|denied|active|completed|expired)$")
    approval_notes: Optional[str] = None
    admin_notes: Optional[str] = None

class LocationResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    default_duration: int
    requires_approval: bool
    is_active: bool
    is_early_release_only: bool
    is_summons_only: bool
    room_number: Optional[str]

class AvailableLocationsResponse(BaseModel):
    pre_approved: List[LocationResponse]
    requires_approval: List[LocationResponse] 