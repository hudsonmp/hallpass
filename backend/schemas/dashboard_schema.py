from pydantic import BaseModel, Field
from typing import Union, Optional, List, Dict, Any

class AnalyticsData(BaseModel):
    average_pass_duration: Optional[float] = None
    total_passes_day: Optional[int] = None
    total_passes_week: Optional[int] = None
    total_passes_month: Optional[int] = None
    status: str = "success"

class TeacherMetrics(BaseModel):
    passes_granted_week: Optional[int] = None
    passes_granted_month: Optional[int] = None
    average_pass_duration: Optional[float] = None
    status: str = "success"

class SchoolAverages(BaseModel):
    avg_passes_per_teacher_week: Optional[float] = None
    avg_passes_per_teacher_month: Optional[float] = None
    avg_duration_school_wide: Optional[float] = None
    status: str = "success"

class TeacherAnalyticsData(AnalyticsData):
    school_average_duration: Optional[float] = None

class NotEnoughData(BaseModel):
    status: str = Field("Not Enough Data", const=True)

class AdminDashboard(BaseModel):
    analytics: Union[AnalyticsData, NotEnoughData]

class TeacherDashboard(BaseModel):
    teacher_metrics: Union[TeacherMetrics, NotEnoughData]
    school_averages: Union[SchoolAverages, NotEnoughData]

class StudentDashboard(BaseModel):
    recent_passes: List[Dict[str, Any]] = []
    active_pass: Optional[Dict[str, Any]] = None
    total_passes: int = 0 