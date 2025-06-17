from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid

class SchoolSettingsUpdate(BaseModel):
    default_pass_duration: Optional[int] = Field(None, gt=0)
    concurrent_pass_limit: Optional[int] = Field(None, gt=0)
    pre_approved_settings: Optional[Dict[str, Any]] = None

class School(BaseModel):
    id: uuid.UUID
    name: str
    default_pass_duration: int
    concurrent_pass_limit: int
    pre_approved_settings: Optional[Dict[str, Any]]

    class Config:
        orm_mode = True 