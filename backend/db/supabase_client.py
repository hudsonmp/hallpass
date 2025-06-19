from supabase import create_client, Client
from backend.core.config import settings

def get_supabase_client() -> Client:
    """
    Returns a Supabase client instance with service role key for backend operations.
    This bypasses RLS and is used for privileged server-side operations.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def get_supabase_anon_client() -> Client:
    """
    Returns a Supabase client instance with anon key for authentication operations.
    This is used for user authentication (login/refresh) and respects RLS policies.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Service role client for backend operations
supabase_client = get_supabase_client()

# Anon client for authentication operations  
supabase_anon = get_supabase_anon_client() 