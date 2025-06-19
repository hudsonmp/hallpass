from supabase import create_client, Client
from backend.core.config import settings

def get_supabase_admin_client() -> Client:
    """
    Returns a Supabase client with SERVICE ROLE key for backend operations.
    This client bypasses RLS and should only be used server-side.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def get_supabase_anon_client() -> Client:
    """
    Returns a Supabase client with ANON key for authentication operations.
    This client respects RLS policies and is safe for auth operations.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Default client for backward compatibility (using service role)
supabase_client = get_supabase_admin_client()

# Separate clients for different purposes
supabase_admin = get_supabase_admin_client()  # For backend data operations
supabase_auth = get_supabase_anon_client()     # For authentication operations 