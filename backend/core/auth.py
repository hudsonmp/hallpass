from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any
from backend.db.supabase_client import supabase_client
from backend.core.config import settings

auth_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(auth_scheme)) -> Dict[str, Any]:
    """
    Extract and validate the current user from the JWT token using Supabase service role client.
    This is the main dependency for protecting routes.
    """
    token = credentials.credentials
    
    try:
        # Validate and fetch user via Supabase using service role client
        user_resp = supabase_client.auth.get_user(token)
        user = user_resp.user
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Fetch the user's role from profiles table (service key bypasses RLS)
        profile_response = supabase_client.table("profiles").select("role, school_id").eq("id", user.id).execute()
        
        if not profile_response.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile/role not found"
            )
        
        role = profile_response.data[0]["role"]
        school_id = profile_response.data[0]["school_id"]
        
        # Return user info with role
        return {
            "id": user.id,
            "email": user.email,
            "role": role,
            "school_id": school_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_role(required_roles: List[str]):
    """
    Create a dependency that requires specific roles.
    Admins are considered to have all permissions (hierarchical role handling).
    Provides helpful error messages with redirect guidance instead of just 403 errors.
    
    Args:
        required_roles: List of roles that are allowed to access the endpoint
        
    Returns:
        A dependency function that validates user role
    """
    def _role_dependency(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user["role"]
        
        # Admins have all permissions (hierarchical access)
        if user_role == "administrator":
            return current_user
            
        # Check if user role is in the required roles
        if user_role not in required_roles:
            # Provide role-specific redirect guidance
            role_redirects = {
                "student": "/api/v1/dashboard/student",
                "teacher": "/api/v1/dashboard/teacher",
                "administrator": "/api/v1/dashboard/admin"
            }
            
            suggested_redirect = role_redirects.get(user_role, "/api/v1/auth/redirect")
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": f"Access denied. This endpoint requires role {required_roles}, but user has role '{user_role}'",
                    "user_role": user_role,
                    "required_roles": required_roles,
                    "suggested_redirect": suggested_redirect,
                    "redirect_endpoint": "/api/v1/auth/redirect"
                }
            )
        
        return current_user
    
    return _role_dependency

def require_student_role(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency that requires student role."""
    return require_role(["student"])(current_user)

def require_teacher_role(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency that requires teacher or admin role."""
    return require_role(["teacher", "administrator"])(current_user)

def require_admin_role(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency that requires admin role only."""
    return require_role(["administrator"])(current_user)

def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get the full user profile including school information.
    This is an enhanced version that returns complete profile data.
    """
    try:
        # Query the profiles table with school information using service role
        response = supabase_client.table('profiles').select(
            'id, email, first_name, last_name, role, school_id, student_id, teacher_id, grade_level, department, schools(name)'
        ).eq('id', current_user["id"]).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        profile_data = response.data
        school_name = profile_data['schools']['name'] if profile_data['schools'] else "Unknown School"
        
        return {
            "id": profile_data['id'],
            "email": profile_data['email'],
            "first_name": profile_data['first_name'],
            "last_name": profile_data['last_name'],
            "role": profile_data['role'],
            "school_id": profile_data['school_id'],
            "school_name": school_name,
            "student_id": profile_data.get('student_id'),
            "teacher_id": profile_data.get('teacher_id'),
            "grade_level": profile_data.get('grade_level'),
            "department": profile_data.get('department')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user profile: {str(e)}"
        ) from e