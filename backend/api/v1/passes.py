from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timedelta
from backend.db.supabase_client import supabase_admin
from backend.api.v1.auth import get_current_user, require_student, require_teacher, require_admin

router = APIRouter(prefix="/passes", tags=["passes"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class PassRequest(BaseModel):
    location_id: uuid.UUID
    student_reason: Optional[str] = None
    requested_start_time: Optional[datetime] = None
    requested_end_time: Optional[datetime] = None

class PassIssue(BaseModel):
    student_id: uuid.UUID
    location_id: uuid.UUID
    duration_minutes: Optional[int] = None
    admin_notes: Optional[str] = None
    is_summons: bool = False
    is_early_release: bool = False

class PassUpdate(BaseModel):
    status: Optional[str] = None
    approval_notes: Optional[str] = None
    admin_notes: Optional[str] = None

class PassResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    location_id: uuid.UUID
    location_name: str
    status: str
    created_at: datetime
    requested_start_time: Optional[datetime]
    actual_start_time: Optional[datetime]
    requested_end_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    duration_minutes: Optional[int]
    approver_id: Optional[uuid.UUID]
    approver_name: Optional[str]
    approved_at: Optional[datetime]
    approval_notes: Optional[str]
    student_reason: Optional[str]
    admin_notes: Optional[str]
    is_summons: bool
    is_early_release: bool
    verification_code: Optional[str]

# ============================================================================
# STUDENT ENDPOINTS
# ============================================================================

@router.post("/request", response_model=PassResponse)
async def request_pass(
    pass_data: PassRequest,
    current_user: Dict[str, Any] = Depends(require_student)
):
    """
    Students can create their own hall pass requests.
    Approval depends on location settings and pre-approved configurations.
    """
    try:
        student_id = current_user["id"]
        school_id = current_user["school_id"]
        
        # Verify location exists and belongs to the school
        location_response = supabase_admin.table("locations").select(
            "id, name, default_duration, requires_approval, is_early_release_only, is_summons_only"
        ).eq("id", pass_data.location_id).eq("school_id", school_id).execute()
        
        if not location_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found or not available for your school"
            )
        
        location = location_response.data[0]
        
        # Check if location requires special conditions
        if location["is_early_release_only"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This location requires an early release pass"
            )
        
        if location["is_summons_only"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This location is only available when summoned"
            )
        
        # Set pass timing
        start_time = pass_data.requested_start_time or datetime.utcnow()
        duration = location["default_duration"]
        end_time = pass_data.requested_end_time or (start_time + timedelta(minutes=duration))
        
        # Determine initial status
        initial_status = "approved" if not location["requires_approval"] else "pending"
        
        # Create the pass
        pass_insert = {
            "school_id": school_id,
            "student_id": student_id,
            "location_id": pass_data.location_id,
            "status": initial_status,
            "requested_start_time": start_time.isoformat(),
            "requested_end_time": end_time.isoformat(),
            "student_reason": pass_data.student_reason,
            "duration_minutes": duration
        }
        
        # If auto-approved, set approver as system
        if initial_status == "approved":
            pass_insert["approved_at"] = datetime.utcnow().isoformat()
            pass_insert["approval_notes"] = "Auto-approved based on location settings"
        
        response = supabase_admin.table("passes").insert(pass_insert).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create pass request"
            )
        
        # Return the created pass with full details
        return await get_pass_details(response.data[0]["id"], current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating pass request: {str(e)}"
        )

@router.get("/mine", response_model=List[PassResponse])
async def get_my_passes(
    status_filter: Optional[str] = Query(None, description="Filter by pass status"),
    current_user: Dict[str, Any] = Depends(require_student)
):
    """
    Students can view their own passes (past, current, and future).
    """
    try:
        query = supabase_admin.table("passes").select(
            """
            id, student_id, location_id, status, created_at,
            requested_start_time, actual_start_time, requested_end_time, actual_end_time,
            duration_minutes, approver_id, approved_at, approval_notes,
            student_reason, admin_notes, is_summons, is_early_release, verification_code,
            locations(name),
            profiles!approver_id(first_name, last_name)
            """
        ).eq("student_id", current_user["id"]).order("created_at", desc=True)
        
        if status_filter:
            query = query.eq("status", status_filter)
        
        response = query.execute()
        
        passes = []
        for pass_data in response.data:
            approver_name = None
            if pass_data.get("profiles"):
                approver = pass_data["profiles"]
                approver_name = f"{approver['first_name']} {approver['last_name']}"
            
            passes.append(PassResponse(
                id=pass_data["id"],
                student_id=pass_data["student_id"],
                student_name=f"{current_user['first_name']} {current_user['last_name']}",
                location_id=pass_data["location_id"],
                location_name=pass_data["locations"]["name"],
                status=pass_data["status"],
                created_at=pass_data["created_at"],
                requested_start_time=pass_data.get("requested_start_time"),
                actual_start_time=pass_data.get("actual_start_time"),
                requested_end_time=pass_data.get("requested_end_time"),
                actual_end_time=pass_data.get("actual_end_time"),
                duration_minutes=pass_data.get("duration_minutes"),
                approver_id=pass_data.get("approver_id"),
                approver_name=approver_name,
                approved_at=pass_data.get("approved_at"),
                approval_notes=pass_data.get("approval_notes"),
                student_reason=pass_data.get("student_reason"),
                admin_notes=pass_data.get("admin_notes"),
                is_summons=pass_data.get("is_summons", False),
                is_early_release=pass_data.get("is_early_release", False),
                verification_code=pass_data.get("verification_code")
            ))
        
        return passes
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching passes: {str(e)}"
        )

@router.post("/{pass_id}/activate", response_model=PassResponse)
async def activate_pass(
    pass_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(require_student)
):
    """
    Students can activate their approved passes to get QR code.
    """
    try:
        # Verify the pass belongs to the current student
        pass_response = supabase_admin.table("passes").select("*").eq(
            "id", pass_id
        ).eq("student_id", current_user["id"]).execute()
        
        if not pass_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pass not found"
            )
        
        pass_data = pass_response.data[0]
        
        if pass_data["status"] != "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pass must be approved before activation"
            )
        
        # Update pass to active status (trigger will set verification code)
        update_response = supabase_admin.table("passes").update({
            "status": "active"
        }).eq("id", pass_id).execute()
        
        if not update_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to activate pass"
            )
        
        return await get_pass_details(pass_id, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error activating pass: {str(e)}"
        )

# ============================================================================
# TEACHER ENDPOINTS
# ============================================================================

@router.post("/issue", response_model=PassResponse)
async def issue_pass(
    pass_data: PassIssue,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """
    Teachers and admins can create and assign passes directly to students.
    """
    try:
        school_id = current_user["school_id"]
        
        # Verify student exists and belongs to the same school
        student_response = supabase_admin.table("profiles").select(
            "id, first_name, last_name, school_id"
        ).eq("id", pass_data.student_id).eq("school_id", school_id).execute()
        
        if not student_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in your school"
            )
        
        # Verify location exists
        location_response = supabase_admin.table("locations").select(
            "id, name, default_duration"
        ).eq("id", pass_data.location_id).eq("school_id", school_id).execute()
        
        if not location_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found"
            )
        
        location = location_response.data[0]
        duration = pass_data.duration_minutes or location["default_duration"]
        
        # Create the pass (teacher-issued passes are auto-approved)
        pass_insert = {
            "school_id": school_id,
            "student_id": pass_data.student_id,
            "location_id": pass_data.location_id,
            "status": "approved",
            "approver_id": current_user["id"],
            "approved_at": datetime.utcnow().isoformat(),
            "duration_minutes": duration,
            "admin_notes": pass_data.admin_notes,
            "is_summons": pass_data.is_summons,
            "is_early_release": pass_data.is_early_release,
            "approval_notes": f"Issued by {current_user['role']} {current_user['first_name']} {current_user['last_name']}"
        }
        
        response = supabase_admin.table("passes").insert(pass_insert).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to issue pass"
            )
        
        return await get_pass_details(response.data[0]["id"], current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error issuing pass: {str(e)}"
        )

@router.get("/pending", response_model=List[PassResponse])
async def get_pending_passes(current_user: Dict[str, Any] = Depends(require_teacher)):
    """
    Teachers can view pending pass requests that need approval.
    """
    try:
        response = supabase_admin.table("passes").select(
            """
            id, student_id, location_id, status, created_at,
            requested_start_time, requested_end_time, duration_minutes,
            student_reason, is_summons, is_early_release,
            locations(name),
            profiles!student_id(first_name, last_name)
            """
        ).eq("school_id", current_user["school_id"]).eq("status", "pending").order("created_at").execute()
        
        passes = []
        for pass_data in response.data:
            student = pass_data["profiles"]
            student_name = f"{student['first_name']} {student['last_name']}"
            
            passes.append(PassResponse(
                id=pass_data["id"],
                student_id=pass_data["student_id"],
                student_name=student_name,
                location_id=pass_data["location_id"],
                location_name=pass_data["locations"]["name"],
                status=pass_data["status"],
                created_at=pass_data["created_at"],
                requested_start_time=pass_data.get("requested_start_time"),
                actual_start_time=None,
                requested_end_time=pass_data.get("requested_end_time"),
                actual_end_time=None,
                duration_minutes=pass_data.get("duration_minutes"),
                approver_id=None,
                approver_name=None,
                approved_at=None,
                approval_notes=None,
                student_reason=pass_data.get("student_reason"),
                admin_notes=None,
                is_summons=pass_data.get("is_summons", False),
                is_early_release=pass_data.get("is_early_release", False),
                verification_code=None
            ))
        
        return passes
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pending passes: {str(e)}"
        )

@router.put("/{pass_id}/approve", response_model=PassResponse)
async def approve_pass(
    pass_id: uuid.UUID,
    approval_data: PassUpdate,
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """
    Teachers can approve or deny pending pass requests.
    """
    try:
        # Verify pass exists and belongs to the teacher's school
        pass_response = supabase_admin.table("passes").select("*").eq(
            "id", pass_id
        ).eq("school_id", current_user["school_id"]).execute()
        
        if not pass_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pass not found"
            )
        
        pass_data = pass_response.data[0]
        
        if pass_data["status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pass is not pending approval"
            )
        
        # Update pass status
        update_data = {
            "status": approval_data.status or "approved",
            "approver_id": current_user["id"],
            "approved_at": datetime.utcnow().isoformat(),
            "approval_notes": approval_data.approval_notes or f"Processed by {current_user['first_name']} {current_user['last_name']}"
        }
        
        if approval_data.admin_notes:
            update_data["admin_notes"] = approval_data.admin_notes
        
        response = supabase_admin.table("passes").update(update_data).eq("id", pass_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update pass"
            )
        
        return await get_pass_details(pass_id, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating pass: {str(e)}"
        )

@router.get("/school", response_model=List[PassResponse])
async def get_school_passes(
    status_filter: Optional[str] = Query(None, description="Filter by pass status"),
    student_name: Optional[str] = Query(None, description="Search by student name"),
    current_user: Dict[str, Any] = Depends(require_teacher)
):
    """
    Teachers can view all passes from their school with optional filtering.
    """
    try:
        query = supabase_admin.table("passes").select(
            """
            id, student_id, location_id, status, created_at,
            requested_start_time, actual_start_time, requested_end_time, actual_end_time,
            duration_minutes, approver_id, approved_at, approval_notes,
            student_reason, admin_notes, is_summons, is_early_release, verification_code,
            locations(name),
            profiles!student_id(first_name, last_name),
            profiles!approver_id(first_name, last_name)
            """
        ).eq("school_id", current_user["school_id"]).order("created_at", desc=True)
        
        if status_filter:
            query = query.eq("status", status_filter)
        
        response = query.execute()
        
        passes = []
        for pass_data in response.data:
            # Get student name
            student = pass_data["profiles"]
            if isinstance(student, list):
                student = student[0] if student else {}
            student_name_full = f"{student.get('first_name', '')} {student.get('last_name', '')}" if student else "Unknown Student"
            
            # Handle search filter
            if student_name and student_name.lower() not in student_name_full.lower():
                continue
            
            # Get approver name (if exists)
            approver_name = None
            if pass_data.get("approver_id"):
                # This is a bit tricky with the current query structure, for now we'll handle it simply
                approver_name = "Staff Member"  # Could be enhanced with another query
            
            passes.append(PassResponse(
                id=pass_data["id"],
                student_id=pass_data["student_id"],
                student_name=student_name_full,
                location_id=pass_data["location_id"],
                location_name=pass_data["locations"]["name"],
                status=pass_data["status"],
                created_at=pass_data["created_at"],
                requested_start_time=pass_data.get("requested_start_time"),
                actual_start_time=pass_data.get("actual_start_time"),
                requested_end_time=pass_data.get("requested_end_time"),
                actual_end_time=pass_data.get("actual_end_time"),
                duration_minutes=pass_data.get("duration_minutes"),
                approver_id=pass_data.get("approver_id"),
                approver_name=approver_name,
                approved_at=pass_data.get("approved_at"),
                approval_notes=pass_data.get("approval_notes"),
                student_reason=pass_data.get("student_reason"),
                admin_notes=pass_data.get("admin_notes"),
                is_summons=pass_data.get("is_summons", False),
                is_early_release=pass_data.get("is_early_release", False),
                verification_code=pass_data.get("verification_code")
            ))
        
        return passes
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching school passes: {str(e)}"
        )

# ============================================================================
# SHARED ENDPOINTS (VIEW ACCESS)
# ============================================================================

@router.get("/{pass_id}", response_model=PassResponse)
async def get_pass(
    pass_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get specific pass details. Students can only see their own, teachers/admins can see any from their school.
    """
    try:
        return await get_pass_details(pass_id, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pass: {str(e)}"
        )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_pass_details(pass_id: uuid.UUID, current_user: Optional[Dict[str, Any]] = None) -> PassResponse:
    """
    Helper function to get complete pass details with proper authorization.
    """
    query = supabase_admin.table("passes").select(
        """
        id, student_id, location_id, status, created_at, school_id,
        requested_start_time, actual_start_time, requested_end_time, actual_end_time,
        duration_minutes, approver_id, approved_at, approval_notes,
        student_reason, admin_notes, is_summons, is_early_release, verification_code,
        locations(name),
        profiles!student_id(first_name, last_name),
        profiles!approver_id(first_name, last_name)
        """
    ).eq("id", pass_id)
    
    response = query.execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pass not found"
        )
    
    pass_data = response.data[0]
    
    # Authorization check if current_user provided
    if current_user:
        user_role = current_user["role"]
        if user_role == "student" and pass_data["student_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only view their own passes"
            )
        elif user_role in ["teacher", "administrator"] and pass_data["school_id"] != current_user["school_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to passes from other schools"
            )
    
    # Get student and approver names
    student = pass_data["profiles"]
    if isinstance(student, list):
        student = student[0] if student else {}
    student_name = f"{student.get('first_name', '')} {student.get('last_name', '')}" if student else "Unknown Student"
    
    approver_name = None
    if pass_data.get("approver_id"):
        # For simplicity, we'll show "Staff Member" - could be enhanced with proper join
        approver_name = "Staff Member"
    
    return PassResponse(
        id=pass_data["id"],
        student_id=pass_data["student_id"],
        student_name=student_name,
        location_id=pass_data["location_id"],
        location_name=pass_data["locations"]["name"],
        status=pass_data["status"],
        created_at=pass_data["created_at"],
        requested_start_time=pass_data.get("requested_start_time"),
        actual_start_time=pass_data.get("actual_start_time"),
        requested_end_time=pass_data.get("requested_end_time"),
        actual_end_time=pass_data.get("actual_end_time"),
        duration_minutes=pass_data.get("duration_minutes"),
        approver_id=pass_data.get("approver_id"),
        approver_name=approver_name,
        approved_at=pass_data.get("approved_at"),
        approval_notes=pass_data.get("approval_notes"),
        student_reason=pass_data.get("student_reason"),
        admin_notes=pass_data.get("admin_notes"),
        is_summons=pass_data.get("is_summons", False),
        is_early_release=pass_data.get("is_early_release", False),
        verification_code=pass_data.get("verification_code")
    ) 