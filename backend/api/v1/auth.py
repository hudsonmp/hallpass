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

@router.post("/login", response_model=AuthTokens)
async def login(credentials: LoginRequest):
    """
    Authenticates a user with email and password via Supabase and returns access and refresh tokens along with user role information.
    
    Returns:
        AuthTokens: Contains access token, refresh token, token type, and public user information (email and role).
    
    Raises:
        HTTPException: If authentication fails or the user profile is not found.
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
    Exchanges a refresh token for new access and refresh tokens, returning updated authentication tokens and user information.
    
    Parameters:
        payload (RefreshRequest): Contains the refresh token to be exchanged.
    
    Returns:
        AuthTokens: New access and refresh tokens along with user email and role.
    
    Raises:
        HTTPException: If the refresh token is invalid or the user profile cannot be found.
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

@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Logs out the current authenticated user by invalidating their Supabase session.
    
    Returns:
        dict: A message indicating successful logout, regardless of Supabase sign-out outcome.
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
    Retrieve the authenticated user's detailed profile information.
    
    Returns:
        UserProfile: The current user's profile including ID, email, name, role, and school details.
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
    Check if the current user is authenticated and return basic user information.
    
    Returns:
        dict: Contains authentication status and user details including user ID, email, role, and school ID.
    """
    return {
        "authenticated": True,
        "user_id": current_user["id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "school_id": current_user["school_id"]
    } 