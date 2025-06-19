from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
import uuid
from backend.db.supabase_client import supabase_admin, supabase_auth
from backend.core.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])
auth_scheme = HTTPBearer()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class UserPublic(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    first_name: str
    last_name: str
    school_id: uuid.UUID
    school_name: str

class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic

class AuthResponse(BaseModel):
    authenticated: bool
    user_id: uuid.UUID
    email: str
    role: str

# ============================================================================
# CORE AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)
) -> Dict[str, Any]:
    """
    Extract and validate the current user from the JWT token using Supabase Auth.
    Returns user info with role for authorization checks.
    """
    try:
        token = credentials.credentials
        
        # Validate token with Supabase Auth
        user_response = supabase_admin.auth.get_user(token)
        
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = user_response.user
        
        # Fetch user's role and profile from profiles table using service key
        profile_response = supabase_admin.table("profiles").select(
            "id, email, first_name, last_name, role, school_id, schools(name)"
        ).eq("id", user.id).execute()
        
        if not profile_response.data:
            raise HTTPException(
                status_code=status.HTTP_403_UNAUTHORIZED,
                detail="User profile/role not found"
            )
        
        profile = profile_response.data[0]
        school_name = profile.get('schools', {}).get('name', 'Unknown School') if profile.get('schools') else 'Unknown School'
        
        return {
            "id": user.id,
            "email": user.email,
            "role": profile["role"],
            "first_name": profile["first_name"],
            "last_name": profile["last_name"],
            "school_id": profile["school_id"],
            "school_name": school_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_role(required_roles: List[str]):
    """
    Creates a dependency that requires the user to have one of the specified roles.
    Administrators are considered to have all permissions (hierarchical role handling).
    
    Args:
        required_roles: List of roles that are allowed to access the endpoint
        
    Returns:
        Dependency function that validates user role
    """
    def _role_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_role = current_user["role"]
        
        # Hierarchical role handling: admins can access any endpoint
        if user_role == "administrator":
            return current_user
            
        # Check if user has required role
        if user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: requires role {required_roles}, but user has role '{user_role}'"
            )
        return current_user
    
    return _role_dependency

# Role-specific dependencies for common use cases
require_student = require_role(["student"])
require_teacher = require_role(["teacher", "administrator"])  # Teachers and admins
require_admin = require_role(["administrator"])

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/login", response_model=AuthTokens)
async def login(credentials: LoginRequest):
    """
    Authenticate user with email and password using Supabase Auth.
    Returns JWT access token, refresh token, and user profile information.
    """
    try:
        # Authenticate with Supabase using anon client
        auth_response = supabase_auth.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = auth_response.user
        session = auth_response.session
        
        # Get user profile using service key (to bypass RLS for server operations)
        profile_response = supabase_admin.table("profiles").select(
            "id, email, first_name, last_name, role, school_id, schools(name)"
        ).eq("id", user.id).execute()
        
        if not profile_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found. Please contact administrator."
            )
        
        profile = profile_response.data[0]
        school_name = profile.get('schools', {}).get('name', 'Unknown School') if profile.get('schools') else 'Unknown School'
        
        user_public = UserPublic(
            id=profile["id"],
            email=profile["email"],
            role=profile["role"],
            first_name=profile["first_name"],
            last_name=profile["last_name"],
            school_id=profile["school_id"],
            school_name=school_name
        )
        
        return AuthTokens(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user=user_public
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

@router.post("/refresh", response_model=AuthTokens)
async def refresh_session(payload: RefreshRequest):
    """
    Exchange refresh token for new access and refresh tokens.
    Refresh tokens are single-use in Supabase.
    """
    try:
        # Use anon client for refresh operations
        refresh_response = supabase_auth.auth.refresh_session(payload.refresh_token)
        
        if not refresh_response.session or not refresh_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        session = refresh_response.session
        user = refresh_response.user
        
        # Get updated user profile
        profile_response = supabase_admin.table("profiles").select(
            "id, email, first_name, last_name, role, school_id, schools(name)"
        ).eq("id", user.id).execute()
        
        if not profile_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        profile = profile_response.data[0]
        school_name = profile.get('schools', {}).get('name', 'Unknown School') if profile.get('schools') else 'Unknown School'
        
        user_public = UserPublic(
            id=profile["id"],
            email=profile["email"],
            role=profile["role"],
            first_name=profile["first_name"],
            last_name=profile["last_name"],
            school_id=profile["school_id"],
            school_name=school_name
        )
        
        return AuthTokens(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user=user_public
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Logout the current user by invalidating their session.
    """
    try:
        supabase_auth.auth.sign_out()
        return {"message": "Successfully logged out"}
    
    except Exception as e:
        # Even if logout fails, return success to client
        return {"message": "Logout completed"}

@router.get("/me", response_model=UserPublic)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current authenticated user's profile information.
    Available to any authenticated user.
    """
    return UserPublic(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        first_name=current_user["first_name"],
        last_name=current_user["last_name"],
        school_id=current_user["school_id"],
        school_name=current_user["school_name"]
    )

@router.get("/check", response_model=AuthResponse)
async def check_auth(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Simple endpoint to check if user is authenticated and return basic info.
    """
    return AuthResponse(
        authenticated=True,
        user_id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"]
    )

# ============================================================================
# DEMO ENDPOINTS FOR ROLE TESTING
# ============================================================================

@router.get("/student-only")
async def student_only_endpoint(current_user: Dict[str, Any] = Depends(require_student)):
    """Demo endpoint - Students only"""
    return {"message": f"Hello student {current_user['first_name']}!", "role": current_user["role"]}

@router.get("/teacher-only") 
async def teacher_only_endpoint(current_user: Dict[str, Any] = Depends(require_teacher)):
    """Demo endpoint - Teachers and Admins only"""
    return {"message": f"Hello {current_user['role']} {current_user['first_name']}!", "role": current_user["role"]}

@router.get("/admin-only")
async def admin_only_endpoint(current_user: Dict[str, Any] = Depends(require_admin)):
    """Demo endpoint - Administrators only"""
    return {"message": f"Hello administrator {current_user['first_name']}!", "role": current_user["role"]} 