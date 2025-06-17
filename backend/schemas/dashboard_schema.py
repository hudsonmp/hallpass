from pydantic import BaseModel, Field
from typing import Union

class AnalyticsData(BaseModel):
    average_pass_duration: float
    total_passes_day: int
    total_passes_week: int
    total_passes_month: int

class TeacherAnalyticsData(AnalyticsData):
    school_average_duration: float

class NotEnoughData(BaseModel):
    status: str = Field("Not Enough Data", const=True)

class AdminDashboard(BaseModel):
    analytics: Union[AnalyticsData, NotEnoughData]

class TeacherDashboard(BaseModel):
    analytics: Union[TeacherAnalyticsData, NotEnoughData] 