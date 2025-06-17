from supabase import create_client, Client
from backend.core.config import settings

def get_supabase_client() -> Client:
    """
    Returns a Supabase client instance.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

supabase_client = get_supabase_client() 