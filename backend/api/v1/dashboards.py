from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from datetime import datetime, timedelta

from backend.db.supabase_client import supabase_client
from backend.core.auth import get_current_user, require_admin_role, require_teacher_role
from backend.schemas import dashboard_schema

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboards & Analytics"],
)

@router.get("/admin", response_model=dashboard_schema.AdminDashboard)
async def get_admin_dashboard(current_user: Dict[str, Any] = Depends(require_admin_role)):
    """
    Get admin dashboard analytics (Admins only).
    Shows school-wide metrics and statistics.
    """
    try:
        school_id = current_user["school_id"]
        
        # Fetch all completed passes for the school
        response = supabase_client.table('passes').select(
            "actual_start_time, actual_end_time, created_at, duration_minutes"
        ).eq('school_id', str(school_id)).eq('status', 'completed').execute()
        
        passes = response.data
        
        if not passes:
            # Return "Not Enough Data" structure when no data available
            return dashboard_schema.AdminDashboard(
                analytics=dashboard_schema.AnalyticsData(
                    average_pass_duration=None,
                    total_passes_day=None,
                    total_passes_week=None,
                    total_passes_month=None,
                    status="Not Enough Data"
                )
            )

        # Calculate time boundaries
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Initialize counters
        total_duration = 0
        valid_passes_for_avg = 0
        passes_today = 0
        passes_week = 0
        passes_month = 0

        for pass_record in passes:
            created_at = datetime.fromisoformat(pass_record['created_at'].replace('Z', '+00:00'))
            
            # Count passes by time period
            if created_at >= day_ago:
                passes_today += 1
            if created_at >= week_ago:
                passes_week += 1
            if created_at >= month_ago:
                passes_month += 1
            
            # Calculate average duration from completed passes
            if pass_record.get('duration_minutes'):
                total_duration += pass_record['duration_minutes']
                valid_passes_for_avg += 1

        # Calculate average duration
        average_duration = (total_duration / valid_passes_for_avg) if valid_passes_for_avg > 0 else None

        analytics = dashboard_schema.AnalyticsData(
            average_pass_duration=average_duration,
            total_passes_day=passes_today,
            total_passes_week=passes_week,
            total_passes_month=passes_month,
            status="success"
        )

        return dashboard_schema.AdminDashboard(analytics=analytics)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching admin dashboard: {str(e)}") from e

@router.get("/teacher", response_model=dashboard_schema.TeacherDashboard)
async def get_teacher_dashboard(current_user: Dict[str, Any] = Depends(require_teacher_role)):
    """
    Get teacher dashboard analytics (Teachers and Admins only).
    Shows teacher-specific metrics compared to school averages.
    """
    try:
        school_id = current_user["school_id"]
        teacher_id = current_user["id"]
        
        # Calculate time boundaries
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Get teacher's passes (passes they approved/issued)
        teacher_passes_response = supabase_client.table('passes').select(
            "created_at, duration_minutes, status"
        ).eq('school_id', str(school_id)).eq('approver_id', str(teacher_id)).execute()

        teacher_passes = teacher_passes_response.data or []

        # Get school-wide statistics for comparison
        school_passes_response = supabase_client.table('passes').select(
            "created_at, duration_minutes, approver_id"
        ).eq('school_id', str(school_id)).neq('approver_id', None).execute()

        all_school_passes = school_passes_response.data or []

        if not teacher_passes and not all_school_passes:
            # Return "Not Enough Data" when no data available
            return dashboard_schema.TeacherDashboard(
                teacher_metrics=dashboard_schema.TeacherMetrics(
                    passes_granted_week=None,
                    passes_granted_month=None,
                    average_pass_duration=None,
                    status="Not Enough Data"
                ),
                school_averages=dashboard_schema.SchoolAverages(
                    avg_passes_per_teacher_week=None,
                    avg_passes_per_teacher_month=None,
                    avg_duration_school_wide=None,
                    status="Not Enough Data"
                )
            )

        # Calculate teacher metrics
        teacher_passes_week = 0
        teacher_passes_month = 0
        teacher_total_duration = 0
        teacher_valid_duration_count = 0

        for pass_record in teacher_passes:
            created_at = datetime.fromisoformat(pass_record['created_at'].replace('Z', '+00:00'))
            
            if created_at >= week_ago:
                teacher_passes_week += 1
            if created_at >= month_ago:
                teacher_passes_month += 1
            
            if pass_record.get('duration_minutes'):
                teacher_total_duration += pass_record['duration_minutes']
                teacher_valid_duration_count += 1

        teacher_avg_duration = (teacher_total_duration / teacher_valid_duration_count) if teacher_valid_duration_count > 0 else None

        # Calculate school averages
        school_passes_week = 0
        school_passes_month = 0
        school_total_duration = 0
        school_valid_duration_count = 0
        unique_teachers = set()

        for pass_record in all_school_passes:
            created_at = datetime.fromisoformat(pass_record['created_at'].replace('Z', '+00:00'))
            unique_teachers.add(pass_record['approver_id'])
            
            if created_at >= week_ago:
                school_passes_week += 1
            if created_at >= month_ago:
                school_passes_month += 1
            
            if pass_record.get('duration_minutes'):
                school_total_duration += pass_record['duration_minutes']
                school_valid_duration_count += 1

        teacher_count = len(unique_teachers) if unique_teachers else 1
        school_avg_passes_week = school_passes_week / teacher_count
        school_avg_passes_month = school_passes_month / teacher_count
        school_avg_duration = (school_total_duration / school_valid_duration_count) if school_valid_duration_count > 0 else None

        teacher_metrics = dashboard_schema.TeacherMetrics(
            passes_granted_week=teacher_passes_week,
            passes_granted_month=teacher_passes_month,
            average_pass_duration=teacher_avg_duration,
            status="success"
        )

        school_averages = dashboard_schema.SchoolAverages(
            avg_passes_per_teacher_week=school_avg_passes_week,
            avg_passes_per_teacher_month=school_avg_passes_month,
            avg_duration_school_wide=school_avg_duration,
            status="success"
        )

        return dashboard_schema.TeacherDashboard(
            teacher_metrics=teacher_metrics,
            school_averages=school_averages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching teacher dashboard: {str(e)}") from e

@router.get("/student", response_model=dashboard_schema.StudentDashboard)
async def get_student_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get student dashboard (Students only).
    Shows student's pass history and current status.
    """
    if current_user["role"] != "student":
        raise HTTPException(
            status_code=403,
            detail="Only students can access student dashboard"
        )
    
    try:
        student_id = current_user["id"]
        
        # Get student's recent passes
        passes_response = supabase_client.table('passes').select(
            "*, locations(name), approver:profiles!passes_approver_id_fkey(first_name, last_name)"
        ).eq('student_id', str(student_id)).order('created_at', desc=True).limit(10).execute()

        passes = passes_response.data or []

        # Get current active pass if any
        active_pass_response = supabase_client.table('passes').select(
            "*, locations(name)"
        ).eq('student_id', str(student_id)).eq('status', 'active').single().execute()

        active_pass = active_pass_response.data if active_pass_response.data else None

        return dashboard_schema.StudentDashboard(
            recent_passes=passes,
            active_pass=active_pass,
            total_passes=len(passes)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching student dashboard: {str(e)}") from e 