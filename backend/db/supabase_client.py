from supabase import create_client, Client
from backend.core.config import settings

def get_supabase_client() -> Client:
    """
    Return a Supabase client initialized with the service role key for privileged backend operations.
    
    This client bypasses Row Level Security (RLS) and should only be used for trusted server-side tasks requiring elevated access.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def get_supabase_anon_client() -> Client:
    """
    Return a Supabase client configured with the anon key for authentication-related operations.
    
    This client enforces Row Level Security (RLS) and is intended for user authentication tasks such as login and token refresh.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Service role client for backend operations
supabase_client = get_supabase_client()

# Anon client for authentication operations  
supabase_anon = get_supabase_anon_client() 