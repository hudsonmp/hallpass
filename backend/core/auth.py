from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any
from backend.db.supabase_client import supabase_client
from backend.core.config import settings

auth_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(auth_scheme)) -> Dict[str, Any]:
    """
    Authenticates the current user by validating the JWT token and retrieving user details and role from Supabase.
    
    Returns:
        A dictionary containing the user's id, email, role, and school_id.
    
    Raises:
        HTTPException: If the token is invalid, expired, or the user profile/role is not found.
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
    Returns a dependency that enforces access control based on user roles, granting administrators universal access and restricting others to specified roles.
    
    Parameters:
        required_roles (List[str]): Roles permitted to access the endpoint.
    
    Returns:
        Callable: A dependency function that raises HTTP 403 if the user's role is not authorized.
    """
    def _role_dependency(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        """
        Authorize the current user based on their role, granting access if the user is an administrator or has a required role.
        
        Raises:
            HTTPException: If the user's role is not authorized, with status code 403 Forbidden.
            
        Returns:
            The current user dictionary if authorized.
        """
        user_role = current_user["role"]
        
        # Admins have all permissions (hierarchical access)
        if user_role == "administrator":
            return current_user
            
        # Check if user role is in the required roles
        if user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: requires role {required_roles}, but user has role '{user_role}'"
            )
        
        return current_user
    
    return _role_dependency

def require_student_role(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency that allows access only to users with the "student" role.
    
    Returns:
        The current user dictionary if the user has the "student" role.
    """
    return require_role(["student"])(current_user)

def require_teacher_role(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency that allows access only to users with the "teacher" or "administrator" role.
    
    Returns:
        The current user dictionary if the user has the required role.
    """
    return require_role(["teacher", "administrator"])(current_user)

def require_admin_role(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency that allows access only to users with the administrator role.
    
    Returns:
        The current user dictionary if the user has the administrator role.
    """
    return require_role(["administrator"])(current_user)

def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Retrieve the authenticated user's complete profile, including personal details and associated school information.
    
    Returns:
        A dictionary containing user profile data such as id, email, name, role, school ID, school name, student or teacher IDs, grade level, and department.
    
    Raises:
        HTTPException: If the user profile is not found (404) or if an unexpected error occurs during retrieval (500).
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
        )