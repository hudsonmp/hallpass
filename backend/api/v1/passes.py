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
    Helper function to format pass data from database into PassResponse model.
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
    Get available pass locations for the user's school.
    Returns separate lists for pre-approved and approval-required locations.
    All authenticated users can access this endpoint.
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
    Request a new hall pass (Students only).
    This endpoint creates pass requests that may require teacher approval.
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
    Issue a hall pass directly to a student (Teachers and Admins only).
    This endpoint allows teachers/admins to create and approve passes in one step.
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
    Get passes based on user role.
    Students see only their own passes.
    Teachers and admins see all passes from their school.
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
    Get a specific pass by ID.
    Students can only view their own passes.
    Teachers and admins can view any pass from their school.
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
    Activate an approved pass (Students only).
    This changes the status from 'approved' to 'active' and generates a QR code.
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
    Approve a pending pass request (Teachers and Admins only).
    Changes status from 'pending' to 'approved'.
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