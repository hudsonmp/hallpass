from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import uuid
from backend.db.supabase_client import supabase_client, supabase_anon
from backend.core.auth import get_current_user, get_current_user_profile
from backend.core.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

# Pydantic Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class UserPublic(BaseModel):
    email: EmailStr
    role: str

class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    profile: Dict[str, Any]

class UserProfile(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    school_id: uuid.UUID
    school_name: str

class RoleRedirectResponse(BaseModel):
    redirect_url: str
    role: str
    message: str

@router.post("/login", response_model=AuthTokens)
async def login(credentials: LoginRequest):
    """
    Authenticate user with email and password using Supabase Auth.
    Uses anon key for authentication operations.
    """
    try:
        # Attempt to authenticate with Supabase using anon client
        result = supabase_anon.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        if not result.session or not result.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email or password"
            )
        
        session = result.session
        user = result.user
        
        # Look up the user's role from the profile table using service role client
        profile = supabase_client.table("profiles").select("role").eq("id", user.id).execute()
        
        if not profile.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User profile not found"
            )
        
        role = profile.data[0]["role"]
        
        return AuthTokens(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            token_type="bearer",
            user=UserPublic(email=user.email, role=role)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or password"
        )

@router.post("/refresh", response_model=AuthTokens)
async def refresh_session(payload: RefreshRequest):
    """
    Refresh access token using refresh token.
    Exchange the refresh token for a new access token and refresh token.
    """
    try:
        # Use anon client to refresh the session
        new_session = supabase_anon.auth.refresh_session(payload.refresh_token)
        
        if not new_session.session or not new_session.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        session = new_session.session
        user = new_session.user
        
        # Get role from profile using service role client
        profile = supabase_client.table("profiles").select("role").eq("id", user.id).execute()
        
        if not profile.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User profile not found"
            )
        
        role = profile.data[0]["role"]
        
        return AuthTokens(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            token_type="bearer",
            user=UserPublic(email=user.email, role=role)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/redirect", response_model=RoleRedirectResponse)
async def get_role_redirect(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get the appropriate redirect URL based on user role.
    This endpoint routes users to their role-appropriate dashboard instead of showing 403 errors.
    """
    role = current_user["role"]
    
    # Define role-based redirect URLs
    role_redirects = {
        "administrator": "/api/v1/dashboard/admin",
        "teacher": "/api/v1/dashboard/teacher", 
        "student": "/api/v1/dashboard/student"
    }
    
    redirect_url = role_redirects.get(role)
    
    if not redirect_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown user role: {role}"
        )
    
    return RoleRedirectResponse(
        redirect_url=redirect_url,
        role=role,
        message=f"Redirecting {role} to appropriate dashboard"
    )

@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Logout the current user by invalidating their session.
    Note: With JWT tokens, true logout requires token blacklisting on client side.
    """
    try:
        # Sign out from Supabase (this invalidates the refresh token)
        supabase_anon.auth.sign_out()
        return {"message": "Successfully logged out"}
    
    except Exception as e:
        # Even if Supabase logout fails, we can still return success
        # since the client should discard the tokens
        return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserProfile)
async def get_current_user_info(current_user_profile: Dict[str, Any] = Depends(get_current_user_profile)):
    """
    Get current authenticated user's profile information.
    """
    return UserProfile(
        id=current_user_profile['id'],
        email=current_user_profile['email'],
        first_name=current_user_profile['first_name'],
        last_name=current_user_profile['last_name'],
        role=current_user_profile['role'],
        school_id=current_user_profile['school_id'],
        school_name=current_user_profile['school_name']
    )

@router.get("/check")
async def check_auth(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Simple endpoint to check if user is authenticated.
    Returns basic user information if token is valid.
    """
    return {
        "authenticated": True,
        "user_id": current_user["id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "school_id": current_user["school_id"]
    } 