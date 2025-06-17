from fastapi import APIRouter, HTTPException, Depends
import uuid

from backend.db.supabase_client import supabase_client
from backend.schemas import school_schema

router = APIRouter(
    prefix="/schools",
    tags=["Schools"],
)

@router.get("/{school_id}", response_model=school_schema.School)
def get_school_settings(school_id: uuid.UUID):
    # This endpoint should be protected for admins of that school
    try:
        response = supabase_client.table('schools').select("*").eq('id', str(school_id)).single().execute()
        if response.data:
            return response.data
        raise HTTPException(status_code=404, detail="School not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{school_id}", response_model=school_schema.School)
def update_school_settings(school_id: uuid.UUID, settings: school_schema.SchoolSettingsUpdate):
    # This endpoint should be protected for admins of that school
    try:
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 