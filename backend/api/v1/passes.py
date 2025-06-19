from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
from backend.db.supabase_client import supabase_client
from backend.core.auth import (
    get_current_user, 
    get_current_user_profile, 
    require_student_role,
    require_teacher_role,
    require_admin_role
)
from backend.schemas.pass_schema import (
    PassCreateRequest, 
    PassResponse, 
    PassListResponse, 
    PassStatusUpdate,
    LocationResponse,
    AvailableLocationsResponse
)

router = APIRouter(prefix="/passes", tags=["passes"])

def format_pass_response(pass_data: dict, student_data: dict = None, location_data: dict = None, approver_data: dict = None) -> PassResponse:
    """
    Format raw pass and related entity data into a PassResponse model.
    
    Parameters:
        pass_data (dict): Dictionary containing pass record data from the database.
        student_data (dict, optional): Dictionary with student profile information.
        location_data (dict, optional): Dictionary with location details.
        approver_data (dict, optional): Dictionary with approver profile information.
    
    Returns:
        PassResponse: Structured response model with pass details and related entity names.
    """
    # Get student name
    if student_data:
        student_name = f"{student_data['first_name']} {student_data['last_name']}"
    else:
        student_name = "Unknown Student"
    
    # Get location info
    if location_data:
        location_name = location_data['name']
        location_description = location_data.get('description')
    else:
        location_name = "Unknown Location"
        location_description = None
    
    # Get approver name
    approver_name = None
    if approver_data and pass_data.get('approver_id'):
        approver_name = f"{approver_data['first_name']} {approver_data['last_name']}"
    
    return PassResponse(
        id=pass_data['id'],
        student_id=pass_data['student_id'],
        location_id=pass_data['location_id'],
        school_id=pass_data['school_id'],
        created_at=pass_data['created_at'],
        updated_at=pass_data['updated_at'],
        status=pass_data['status'],
        student_name=student_name,
        student_reason=pass_data.get('student_reason'),
        location_name=location_name,
        location_description=location_description,
        requested_start_time=pass_data.get('requested_start_time'),
        actual_start_time=pass_data.get('actual_start_time'),
        requested_end_time=pass_data.get('requested_end_time'),
        actual_end_time=pass_data.get('actual_end_time'),
        duration_minutes=pass_data.get('duration_minutes'),
        approver_id=pass_data.get('approver_id'),
        approver_name=approver_name,
        approved_at=pass_data.get('approved_at'),
        approval_notes=pass_data.get('approval_notes'),
        is_summons=pass_data.get('is_summons', False),
        is_early_release=pass_data.get('is_early_release', False),
        verification_code=pass_data.get('verification_code'),
        admin_notes=pass_data.get('admin_notes')
    )

@router.get("/locations", response_model=AvailableLocationsResponse)
async def get_available_locations(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retrieve all active pass locations for the current user's school, categorized by whether they require approval.
    
    Returns:
        AvailableLocationsResponse: An object containing two lists—locations that are pre-approved and those that require approval.
    """
    try:
        # Get all active locations for the user's school
        response = supabase_client.table('locations').select('*').eq(
            'school_id', current_user["school_id"]
        ).eq('is_active', True).execute()
        
        if not response.data:
            return AvailableLocationsResponse(pre_approved=[], requires_approval=[])
        
        locations = response.data
        pre_approved = []
        requires_approval = []
        
        for location in locations:
            location_obj = LocationResponse(
                id=location['id'],
                name=location['name'],
                description=location.get('description'),
                default_duration=location['default_duration'],
                requires_approval=location['requires_approval'],
                is_active=location['is_active'],
                is_early_release_only=location.get('is_early_release_only', False),
                is_summons_only=location.get('is_summons_only', False),
                room_number=location.get('room_number')
            )
            
            if location['requires_approval']:
                requires_approval.append(location_obj)
            else:
                pre_approved.append(location_obj)
        
        return AvailableLocationsResponse(
            pre_approved=pre_approved,
            requires_approval=requires_approval
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching locations: {str(e)}"
        )

@router.post("/request", response_model=PassResponse)
async def request_pass(
    pass_request: PassCreateRequest,
    current_user: Dict[str, Any] = Depends(require_student_role)
):
    """
    Allows a student to request a new hall pass, creating a pass that may require teacher approval depending on the location.
    
    Validates the requested location and special requirements, ensures the student does not already have an active pass, and sets the pass status to "pending" if approval is required or "approved" otherwise. Returns the created pass with related student and location information.
    
    Raises:
        HTTPException: If the location is not found, requirements are not met, the student already has an active pass, or if pass creation fails.
    """
    try:
        # Get location details to check requirements
        location_response = supabase_client.table('locations').select('*').eq(
            'id', pass_request.location_id
        ).eq('school_id', current_user["school_id"]).single().execute()
        
        if not location_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found"
            )
        
        location = location_response.data
        
        # Validate special pass requirements
        if location.get('is_summons_only') and not pass_request.is_summons:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This location is only accessible when summoned by staff"
            )
        
        if location.get('is_early_release_only') and not pass_request.is_early_release:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This location is only accessible with an early release pass"
            )
        
        # Check if student already has an active pass
        active_pass_response = supabase_client.table('passes').select('id').eq(
            'student_id', current_user["id"]
        ).in_('status', ['pending', 'approved', 'active']).execute()
        
        if active_pass_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active pass. Please complete or cancel it before creating a new one."
            )
        
        # Calculate requested end time based on location's default duration
        start_time = pass_request.requested_start_time or datetime.utcnow()
        end_time = start_time + timedelta(minutes=location['default_duration'])
        
        # Determine pass status based on approval requirements
        if location['requires_approval']:
            pass_status = 'pending'  # Requires teacher approval
            approved_at = None
        else:
            pass_status = 'approved'  # Pre-approved location
            approved_at = datetime.utcnow().isoformat()
        
        pass_data = {
            'student_id': current_user["id"],
            'location_id': pass_request.location_id,
            'school_id': current_user["school_id"],
            'status': pass_status,
            'requested_start_time': start_time.isoformat(),
            'requested_end_time': end_time.isoformat(),
            'student_reason': pass_request.student_reason,
            'is_summons': pass_request.is_summons,
            'is_early_release': pass_request.is_early_release,
            'approved_at': approved_at
        }
        
        # Insert the pass
        insert_response = supabase_client.table('passes').insert(pass_data).execute()
        
        if not insert_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create pass"
            )
        
        created_pass = insert_response.data[0]
        
        # Get current user profile for response
        current_user_profile = get_current_user_profile(current_user)
        student_data = {
            'first_name': current_user_profile['first_name'],
            'last_name': current_user_profile['last_name']
        }
        
        return format_pass_response(created_pass, student_data, location)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating pass: {str(e)}"
        )

@router.post("/issue", response_model=PassResponse)
async def issue_pass(
    pass_request: PassCreateRequest,
    current_user: Dict[str, Any] = Depends(require_teacher_role)
):
    """
    Issues and approves a hall pass for a student in a single step (teachers and admins only).
    
    Validates the student and location, ensures the student does not already have an active pass, and creates an approved pass with approver information. Returns the formatted pass response including student, location, and approver details.
    
    Raises:
        HTTPException: If the student or location is not found, the student already has an active pass, or if the pass cannot be issued.
    """
    try:
        # Validate that the student exists and belongs to the same school
        student_response = supabase_client.table('profiles').select('*').eq(
            'id', pass_request.student_id
        ).eq('school_id', current_user["school_id"]).eq('role', 'student').single().execute()
        
        if not student_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found or not in your school"
            )
        
        student_data = student_response.data
        
        # Get location details
        location_response = supabase_client.table('locations').select('*').eq(
            'id', pass_request.location_id
        ).eq('school_id', current_user["school_id"]).single().execute()
        
        if not location_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found"
            )
        
        location = location_response.data
        
        # Check if student already has an active pass
        active_pass_response = supabase_client.table('passes').select('id').eq(
            'student_id', pass_request.student_id
        ).in_('status', ['pending', 'approved', 'active']).execute()
        
        if active_pass_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student already has an active pass"
            )
        
        # Calculate end time
        start_time = pass_request.requested_start_time or datetime.utcnow()
        end_time = start_time + timedelta(minutes=location['default_duration'])
        
        pass_data = {
            'student_id': pass_request.student_id,
            'location_id': pass_request.location_id,
            'school_id': current_user["school_id"],
            'status': 'approved',  # Teacher-issued passes are automatically approved
            'requested_start_time': start_time.isoformat(),
            'requested_end_time': end_time.isoformat(),
            'student_reason': pass_request.student_reason,
            'is_summons': pass_request.is_summons,
            'is_early_release': pass_request.is_early_release,
            'approver_id': current_user["id"],
            'approved_at': datetime.utcnow().isoformat(),
            'approval_notes': f"Issued by {current_user['role']}"
        }
        
        # Insert the pass
        insert_response = supabase_client.table('passes').insert(pass_data).execute()
        
        if not insert_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to issue pass"
            )
        
        created_pass = insert_response.data[0]
        
        # Get approver data for response
        approver_profile = get_current_user_profile(current_user)
        approver_data = {
            'first_name': approver_profile['first_name'],
            'last_name': approver_profile['last_name']
        }
        
        return format_pass_response(created_pass, student_data, location, approver_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error issuing pass: {str(e)}"
        )

@router.get("/", response_model=PassListResponse)
async def get_passes(
    status_filter: Optional[str] = Query(None, description="Filter by pass status"),
    limit: int = Query(50, ge=1, le=100, description="Number of passes to return"),
    offset: int = Query(0, ge=0, description="Number of passes to skip"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieve a list of hall passes filtered by status and paginated according to user role.
    
    Students receive only their own passes, while teachers and administrators receive all passes for their school. Passes can be filtered by status and are returned with related student, location, and approver information.
    
    Parameters:
        status_filter (Optional[str]): Optional filter to return passes with a specific status.
        limit (int): Maximum number of passes to return (default 50, range 1–100).
        offset (int): Number of passes to skip for pagination (default 0).
    
    Returns:
        PassListResponse: A response containing the list of passes and the total count.
    """
    try:
        # Build query based on user role
        query = supabase_client.table('passes').select(
            '*, profiles!passes_student_id_fkey(first_name, last_name), '
            'locations(name, description), '
            'approver:profiles!passes_approver_id_fkey(first_name, last_name)'
        )
        
        if current_user["role"] == "student":
            # Students only see their own passes
            query = query.eq('student_id', current_user["id"])
        else:
            # Teachers and admins see all passes from their school
            query = query.eq('school_id', current_user["school_id"])
        
        # Apply status filter if provided
        if status_filter:
            query = query.eq('status', status_filter)
        
        # Apply pagination and ordering
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        
        response = query.execute()
        
        if not response.data:
            return PassListResponse(passes=[], total=0)
        
        # Format pass responses
        formatted_passes = []
        for pass_data in response.data:
            student_data = pass_data.get('profiles')
            location_data = pass_data.get('locations')
            approver_data = pass_data.get('approver')
            
            formatted_pass = format_pass_response(pass_data, student_data, location_data, approver_data)
            formatted_passes.append(formatted_pass)
        
        return PassListResponse(
            passes=formatted_passes,
            total=len(formatted_passes)  # For now, returning actual count
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching passes: {str(e)}"
        )

@router.get("/{pass_id}", response_model=PassResponse)
async def get_pass(
    pass_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieve a specific hall pass by its ID, including related student, location, and approver information.
    
    Students may only access their own passes, while teachers and administrators can access passes from their school. Raises a 404 error if the pass does not exist and a 403 error for unauthorized access.
    
    Returns:
        PassResponse: The formatted pass details with associated student, location, and approver data.
    """
    try:
        # Get the pass with related data
        response = supabase_client.table('passes').select(
            '*, profiles!passes_student_id_fkey(first_name, last_name), '
            'locations(name, description), '
            'approver:profiles!passes_approver_id_fkey(first_name, last_name)'
        ).eq('id', pass_id).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pass not found"
            )
        
        pass_data = response.data
        
        # Check permissions
        if current_user["role"] == "student" and pass_data['student_id'] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own passes"
            )
        elif current_user["role"] in ["teacher", "administrator"] and pass_data['school_id'] != current_user["school_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view passes from your school"
            )
        
        student_data = pass_data.get('profiles')
        location_data = pass_data.get('locations')
        approver_data = pass_data.get('approver')
        
        return format_pass_response(pass_data, student_data, location_data, approver_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pass: {str(e)}"
        )

@router.patch("/{pass_id}/activate", response_model=PassResponse)
async def activate_pass(
    pass_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(require_student_role)
):
    """
    Activates an approved hall pass for the current student, changing its status from 'approved' to 'active' and recording the actual start time.
    
    Raises:
        HTTPException: If the pass is not found, does not belong to the student, is not in 'approved' status, or if activation fails.
    
    Returns:
        PassResponse: The updated pass information including related student, location, and approver details.
    """
    try:
        # Get the pass and verify ownership
        pass_response = supabase_client.table('passes').select('*').eq(
            'id', pass_id
        ).eq('student_id', current_user["id"]).single().execute()
        
        if not pass_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pass not found"
            )
        
        pass_data = pass_response.data
        
        if pass_data['status'] != 'approved':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot activate pass with status '{pass_data['status']}'. Only approved passes can be activated."
            )
        
        # Update pass to active status
        # The verification code will be automatically generated by our database trigger
        update_response = supabase_client.table('passes').update({
            'status': 'active',
            'actual_start_time': datetime.utcnow().isoformat()
        }).eq('id', pass_id).execute()
        
        if not update_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to activate pass"
            )
        
        # Get updated pass with all related data
        updated_response = supabase_client.table('passes').select(
            '*, profiles!passes_student_id_fkey(first_name, last_name), '
            'locations(name, description), '
            'approver:profiles!passes_approver_id_fkey(first_name, last_name)'
        ).eq('id', pass_id).single().execute()
        
        updated_pass = updated_response.data
        student_data = updated_pass.get('profiles')
        location_data = updated_pass.get('locations')
        approver_data = updated_pass.get('approver')
        
        return format_pass_response(updated_pass, student_data, location_data, approver_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error activating pass: {str(e)}"
        )

@router.patch("/{pass_id}/approve", response_model=PassResponse)
async def approve_pass(
    pass_id: uuid.UUID,
    approval_notes: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_teacher_role)
):
    """
    Approves a pending hall pass request by changing its status to 'approved'.
    
    Only teachers and administrators can use this endpoint. Updates the pass with approver information and optional approval notes. Returns the updated pass with related student, location, and approver details.
    
    Parameters:
        pass_id (uuid.UUID): The unique identifier of the pass to approve.
        approval_notes (Optional[str]): Optional notes to include with the approval.
    
    Returns:
        PassResponse: The updated pass with related information.
    
    Raises:
        HTTPException: If the pass is not found, not in 'pending' status, or if an error occurs during approval.
    """
    try:
        # Get the pass and verify it's from the same school
        pass_response = supabase_client.table('passes').select('*').eq(
            'id', pass_id
        ).eq('school_id', current_user["school_id"]).single().execute()
        
        if not pass_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pass not found"
            )
        
        pass_data = pass_response.data
        
        if pass_data['status'] != 'pending':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve pass with status '{pass_data['status']}'. Only pending passes can be approved."
            )
        
        # Update pass to approved status
        update_response = supabase_client.table('passes').update({
            'status': 'approved',
            'approver_id': current_user["id"],
            'approved_at': datetime.utcnow().isoformat(),
            'approval_notes': approval_notes
        }).eq('id', pass_id).execute()
        
        if not update_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to approve pass"
            )
        
        # Get updated pass with all related data
        updated_response = supabase_client.table('passes').select(
            '*, profiles!passes_student_id_fkey(first_name, last_name), '
            'locations(name, description), '
            'approver:profiles!passes_approver_id_fkey(first_name, last_name)'
        ).eq('id', pass_id).single().execute()
        
        updated_pass = updated_response.data
        student_data = updated_pass.get('profiles')
        location_data = updated_pass.get('locations')
        approver_data = updated_pass.get('approver')
        
        return format_pass_response(updated_pass, student_data, location_data, approver_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving pass: {str(e)}"
        ) 