from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import uuid

from backend.db.supabase_client import supabase_client
from backend.core.auth import get_current_user, require_admin_role
from backend.schemas import school_schema

router = APIRouter(
    prefix="/schools",
    tags=["Schools"],
)

@router.get("/me", response_model=school_schema.School)
async def get_current_school_settings(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retrieve the authenticated user's school settings.
    
    Returns the school information associated with the current authenticated user. Raises a 404 error if the school is not found, or a 500 error if an unexpected issue occurs.
    """
    try:
        school_id = current_user["school_id"]
        response = supabase_client.table('schools').select("*").eq('id', str(school_id)).single().execute()
        
        if response.data:
            return response.data
        
        raise HTTPException(status_code=404, detail="School not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching school: {str(e)}")

@router.get("/{school_id}", response_model=school_schema.School)
async def get_school_settings(
    school_id: uuid.UUID, 
    current_user: Dict[str, Any] = Depends(require_admin_role)
):
    """
    Retrieve the settings for a specific school by ID, restricted to admin users accessing their own school.
    
    Raises:
        HTTPException: If the admin attempts to access a different school's settings (403), if the school is not found (404), or if an unexpected error occurs (500).
    
    Returns:
        dict: The school settings data if found.
    """
    try:
        # Ensure admin can only access their own school
        if str(school_id) != current_user["school_id"]:
            raise HTTPException(
                status_code=403, 
                detail="You can only access your own school's settings"
            )
        
        response = supabase_client.table('schools').select("*").eq('id', str(school_id)).single().execute()
        
        if response.data:
            return response.data
        
        raise HTTPException(status_code=404, detail="School not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching school: {str(e)}")

@router.patch("/me", response_model=school_schema.School)
async def update_current_school_settings(
    settings: school_schema.SchoolSettingsUpdate,
    current_user: Dict[str, Any] = Depends(require_admin_role)
):
    """
    Update the authenticated admin user's school settings.
    
    Only administrators can modify their own school's settings. Accepts partial updates; fields not provided will remain unchanged.
    
    Raises:
        HTTPException: If no update data is provided (400), if the school is not found (404), or if the update fails (500).
        
    Returns:
        dict: The updated school settings.
    """
    try:
        school_id = current_user["school_id"]
        update_data = settings.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")

        response = supabase_client.table('schools').update(update_data).eq('id', str(school_id)).execute()

        if response.data:
            # The update operation in Supabase returns the updated records in `data`
            return response.data[0]
        
        # Check if the school exists but nothing was updated, or if the school doesn't exist
        check_school = supabase_client.table('schools').select('id').eq('id', str(school_id)).single().execute()
        if not check_school.data:
            raise HTTPException(status_code=404, detail="School not found")
            
        raise HTTPException(status_code=500, detail="Could not update school settings")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating school: {str(e)}")

@router.patch("/{school_id}", response_model=school_schema.School)
async def update_school_settings(
    school_id: uuid.UUID, 
    settings: school_schema.SchoolSettingsUpdate,
    current_user: Dict[str, Any] = Depends(require_admin_role)
):
    """
    Update the settings of a specific school by its ID, restricted to admin users modifying their own school.
    
    Admins can only update the settings for the school they are associated with. Raises an error if no update data is provided, if the school does not exist, or if the update fails.
    
    Returns:
        dict: The updated school data.
    """
    try:
        # Ensure admin can only modify their own school
        if str(school_id) != current_user["school_id"]:
            raise HTTPException(
                status_code=403, 
                detail="You can only modify your own school's settings"
            )
        
        update_data = settings.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")

        response = supabase_client.table('schools').update(update_data).eq('id', str(school_id)).execute()

        if response.data:
            # The update operation in Supabase returns the updated records in `data`
            return response.data[0]
        
        # Check if the school exists but nothing was updated, or if the school doesn't exist
        check_school = supabase_client.table('schools').select('id').eq('id', str(school_id)).single().execute()
        if not check_school.data:
            raise HTTPException(status_code=404, detail="School not found")
            
        raise HTTPException(status_code=500, detail="Could not update school settings")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating school: {str(e)}") 