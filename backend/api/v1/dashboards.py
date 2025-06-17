from fastapi import APIRouter, HTTPException, Depends
from typing import List
import uuid
from datetime import datetime, timedelta

from backend.db.supabase_client import supabase_client
from backend.schemas import dashboard_schema

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboards & Analytics"],
)

@router.get("/admin/{school_id}", response_model=dashboard_schema.AdminDashboard)
def get_admin_dashboard(school_id: uuid.UUID):
    # This endpoint should be protected for admins of that school
    try:
        # Fetch all 'complete' passes for the school
        response = supabase_client.table('passes').select("start_time, end_time, created_at").eq('school_id', str(school_id)).eq('status', 'complete').execute()
        
        passes = response.data
        if not passes:
            return {"analytics": {"status": "Not Enough Data"}}

        # Placeholder logic for calculations
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        total_duration = 0
        valid_passes_for_avg = 0
        
        passes_day = 0
        passes_week = 0
        passes_month = 0

        for p in passes:
            # Analytics calculations would go here
            pass
            
        # This is placeholder data
        analytics = dashboard_schema.AnalyticsData(
            average_pass_duration=10.5,
            total_passes_day=5,
            total_passes_week=35,
            total_passes_month=150
        )

        return {"analytics": analytics}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 