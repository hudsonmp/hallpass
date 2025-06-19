from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Any, Dict, List, Optional

class ORMBaseModel(BaseModel):
    """Base model with common configuration for ORM and attribute mapping."""

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        # Additional config can be added later 