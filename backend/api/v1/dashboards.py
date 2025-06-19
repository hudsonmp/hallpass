from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from backend.db.supabase_client import supabase_admin
from backend.api.v1.auth import get_current_user, require_teacher, require_admin

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TeacherMetrics(BaseModel):
    passes_granted_week: Optional[int] = None
    passes_granted_month: Optional[int] = None
    avg_absence_duration: Optional[float] = None
    school_avg_passes_week: Optional[int] = None
    school_avg_passes_month: Optional[int] = None
    school_avg_absence_duration: Optional[float] = None
    data_available: bool = True

class AdminMetrics(BaseModel):
    total_passes_today: Optional[int] = None
    total_passes_week: Optional[int] = None
    total_passes_month: Optional[int] = None
    avg_pass_duration: Optional[float] = None
    peak_request_times: Optional[List[Dict[str, Any]]] = None
    data_available: bool = True

class DashboardResponse(BaseModel):
    user_role: str
    metrics: Dict[str, Any]
    message: Optional[str] = None

# ============================================================================
# TEACHER DASHBOARD
# ============================================================================

@router.get("/teacher", response_model=DashboardResponse)
async def get_teacher_dashboard(current_user: Dict[str, Any] = Depends(require_teacher)):
    """
    Teacher dashboard showing pass metrics compared to school-wide averages.
    """
    try:
        user_id = current_user["id"]
        school_id = current_user["school_id"]
        
        # Calculate date ranges
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Get teacher's pass metrics
        teacher_metrics = await get_teacher_metrics(user_id, week_ago, month_ago)
        
        # Get school-wide teacher averages
        school_metrics = await get_school_teacher_averages(school_id, week_ago, month_ago)
        
        # Combine metrics
        metrics = TeacherMetrics(
            passes_granted_week=teacher_metrics.get("week_count"),
            passes_granted_month=teacher_metrics.get("month_count"),
            avg_absence_duration=teacher_metrics.get("avg_duration"),
            school_avg_passes_week=school_metrics.get("avg_week_count"),
            school_avg_passes_month=school_metrics.get("avg_month_count"),
            school_avg_absence_duration=school_metrics.get("avg_duration"),
            data_available=teacher_metrics.get("has_data", False) or school_metrics.get("has_data", False)
        )
        
        message = None
        if not metrics.data_available:
            message = "Not Enough Data"
        
        return DashboardResponse(
            user_role=current_user["role"],
            metrics=metrics.dict(),
            message=message
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching teacher dashboard: {str(e)}"
        )

# ============================================================================
# ADMINISTRATOR DASHBOARD
# ============================================================================

@router.get("/admin", response_model=DashboardResponse)
async def get_admin_dashboard(current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Administrator dashboard showing school-wide hall pass metrics and analytics.
    """
    try:
        school_id = current_user["school_id"]
        
        # Calculate date ranges
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Get school-wide metrics
        admin_metrics = await get_admin_metrics(school_id, today_start, week_ago, month_ago)
        
        # Get peak request times
        peak_times = await get_peak_request_times(school_id, month_ago)
        
        metrics = AdminMetrics(
            total_passes_today=admin_metrics.get("today_count"),
            total_passes_week=admin_metrics.get("week_count"),
            total_passes_month=admin_metrics.get("month_count"),
            avg_pass_duration=admin_metrics.get("avg_duration"),
            peak_request_times=peak_times,
            data_available=admin_metrics.get("has_data", False)
        )
        
        message = None
        if not metrics.data_available:
            message = "Not Enough Data"
        
        return DashboardResponse(
            user_role=current_user["role"],
            metrics=metrics.dict(),
            message=message
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching admin dashboard: {str(e)}"
        )

# ============================================================================
# GENERAL DASHBOARD (ALL ROLES)
# ============================================================================

@router.get("/", response_model=DashboardResponse)
async def get_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    General dashboard endpoint that routes to appropriate role-based dashboard.
    """
    try:
        user_role = current_user["role"]
        
        if user_role == "administrator":
            return await get_admin_dashboard(current_user)
        elif user_role == "teacher":
            return await get_teacher_dashboard(current_user)
        else:
            # Students get basic info
            return DashboardResponse(
                user_role=user_role,
                metrics={
                    "role": user_role,
                    "school_name": current_user["school_name"],
                    "name": f"{current_user['first_name']} {current_user['last_name']}"
                },
                message="Student dashboard - use /passes/mine to see your passes"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching dashboard: {str(e)}"
        )

# ============================================================================
# HELPER FUNCTIONS FOR METRICS CALCULATION
# ============================================================================

async def get_teacher_metrics(teacher_id: str, week_ago: datetime, month_ago: datetime) -> Dict[str, Any]:
    """
    Calculate metrics for a specific teacher.
    """
    try:
        # Get passes approved by this teacher in the last week
        week_response = supabase_admin.table("passes").select(
            "id, duration_minutes, actual_start_time, actual_end_time"
        ).eq("approver_id", teacher_id).gte("approved_at", week_ago.isoformat()).execute()
        
        # Get passes approved by this teacher in the last month
        month_response = supabase_admin.table("passes").select(
            "id, duration_minutes, actual_start_time, actual_end_time"
        ).eq("approver_id", teacher_id).gte("approved_at", month_ago.isoformat()).execute()
        
        week_passes = week_response.data or []
        month_passes = month_response.data or []
        
        # Calculate average duration (using actual duration if available, otherwise requested duration)
        durations = []
        for pass_data in month_passes:
            if pass_data.get("actual_start_time") and pass_data.get("actual_end_time"):
                start = datetime.fromisoformat(pass_data["actual_start_time"].replace('Z', '+00:00'))
                end = datetime.fromisoformat(pass_data["actual_end_time"].replace('Z', '+00:00'))
                duration = (end - start).total_seconds() / 60  # minutes
                durations.append(duration)
            elif pass_data.get("duration_minutes"):
                durations.append(pass_data["duration_minutes"])
        
        avg_duration = sum(durations) / len(durations) if durations else None
        
        return {
            "week_count": len(week_passes),
            "month_count": len(month_passes),
            "avg_duration": round(avg_duration, 2) if avg_duration else None,
            "has_data": len(month_passes) > 0
        }
        
    except Exception:
        return {"week_count": None, "month_count": None, "avg_duration": None, "has_data": False}

async def get_school_teacher_averages(school_id: str, week_ago: datetime, month_ago: datetime) -> Dict[str, Any]:
    """
    Calculate school-wide teacher averages for comparison.
    """
    try:
        # Get all teachers in the school
        teachers_response = supabase_admin.table("profiles").select("id").eq(
            "school_id", school_id
        ).eq("role", "teacher").execute()
        
        if not teachers_response.data:
            return {"avg_week_count": None, "avg_month_count": None, "avg_duration": None, "has_data": False}
        
        teacher_ids = [t["id"] for t in teachers_response.data]
        
        # Get all passes approved by teachers in the school
        week_response = supabase_admin.table("passes").select(
            "approver_id, duration_minutes, actual_start_time, actual_end_time"
        ).in_("approver_id", teacher_ids).gte("approved_at", week_ago.isoformat()).execute()
        
        month_response = supabase_admin.table("passes").select(
            "approver_id, duration_minutes, actual_start_time, actual_end_time"
        ).in_("approver_id", teacher_ids).gte("approved_at", month_ago.isoformat()).execute()
        
        week_passes = week_response.data or []
        month_passes = month_response.data or []
        
        # Calculate averages per teacher
        avg_week_count = len(week_passes) / len(teacher_ids) if teacher_ids else None
        avg_month_count = len(month_passes) / len(teacher_ids) if teacher_ids else None
        
        # Calculate average duration
        durations = []
        for pass_data in month_passes:
            if pass_data.get("actual_start_time") and pass_data.get("actual_end_time"):
                start = datetime.fromisoformat(pass_data["actual_start_time"].replace('Z', '+00:00'))
                end = datetime.fromisoformat(pass_data["actual_end_time"].replace('Z', '+00:00'))
                duration = (end - start).total_seconds() / 60
                durations.append(duration)
            elif pass_data.get("duration_minutes"):
                durations.append(pass_data["duration_minutes"])
        
        avg_duration = sum(durations) / len(durations) if durations else None
        
        return {
            "avg_week_count": round(avg_week_count, 1) if avg_week_count else None,
            "avg_month_count": round(avg_month_count, 1) if avg_month_count else None,
            "avg_duration": round(avg_duration, 2) if avg_duration else None,
            "has_data": len(month_passes) > 0
        }
        
    except Exception:
        return {"avg_week_count": None, "avg_month_count": None, "avg_duration": None, "has_data": False}

async def get_admin_metrics(school_id: str, today_start: datetime, week_ago: datetime, month_ago: datetime) -> Dict[str, Any]:
    """
    Calculate school-wide metrics for administrators.
    """
    try:
        # Get passes for different time periods
        today_response = supabase_admin.table("passes").select("id").eq(
            "school_id", school_id
        ).gte("created_at", today_start.isoformat()).execute()
        
        week_response = supabase_admin.table("passes").select("id").eq(
            "school_id", school_id
        ).gte("created_at", week_ago.isoformat()).execute()
        
        month_response = supabase_admin.table("passes").select(
            "id, duration_minutes, actual_start_time, actual_end_time"
        ).eq("school_id", school_id).gte("created_at", month_ago.isoformat()).execute()
        
        today_count = len(today_response.data) if today_response.data else 0
        week_count = len(week_response.data) if week_response.data else 0
        month_count = len(month_response.data) if month_response.data else 0
        
        # Calculate average pass duration
        month_passes = month_response.data or []
        durations = []
        for pass_data in month_passes:
            if pass_data.get("actual_start_time") and pass_data.get("actual_end_time"):
                start = datetime.fromisoformat(pass_data["actual_start_time"].replace('Z', '+00:00'))
                end = datetime.fromisoformat(pass_data["actual_end_time"].replace('Z', '+00:00'))
                duration = (end - start).total_seconds() / 60
                durations.append(duration)
            elif pass_data.get("duration_minutes"):
                durations.append(pass_data["duration_minutes"])
        
        avg_duration = sum(durations) / len(durations) if durations else None
        
        return {
            "today_count": today_count,
            "week_count": week_count,
            "month_count": month_count,
            "avg_duration": round(avg_duration, 2) if avg_duration else None,
            "has_data": month_count > 0
        }
        
    except Exception:
        return {"today_count": None, "week_count": None, "month_count": None, "avg_duration": None, "has_data": False}

async def get_peak_request_times(school_id: str, month_ago: datetime) -> List[Dict[str, Any]]:
    """
    Calculate the most common times students request passes.
    """
    try:
        # Get all passes from the last month with creation timestamps
        response = supabase_admin.table("passes").select(
            "created_at"
        ).eq("school_id", school_id).gte("created_at", month_ago.isoformat()).execute()
        
        if not response.data:
            return []
        
        # Group by hour of day
        hour_counts = {}
        for pass_data in response.data:
            created_at = datetime.fromisoformat(pass_data["created_at"].replace('Z', '+00:00'))
            hour = created_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Sort by count and return top 5
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        peak_times = []
        for hour, count in sorted_hours:
            # Convert 24-hour to 12-hour format
            if hour == 0:
                time_str = "12:00 AM"
            elif hour < 12:
                time_str = f"{hour}:00 AM"
            elif hour == 12:
                time_str = "12:00 PM"
            else:
                time_str = f"{hour - 12}:00 PM"
            
            peak_times.append({
                "time": time_str,
                "hour": hour,
                "count": count
            })
        
        return peak_times
        
    except Exception:
        return [] 