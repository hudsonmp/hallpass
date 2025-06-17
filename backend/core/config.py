import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Supabase Configuration
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.environ.get("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Project Configuration
    SUPABASE_PROJECT_ID: str = "rxqlewoujpqyvurzzlfv"  # Hallpass project
    
    # Test Data Configuration
    TEST_SCHOOL_ID: str = "fd29756b-2782-4119-9811-6b61443a09de"
    
    # FastAPI Configuration
    BACKEND_API_URL: str = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings() 