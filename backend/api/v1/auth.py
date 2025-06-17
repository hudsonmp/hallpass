from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import uuid
from backend.db.supabase_client import supabase_client
from backend.core.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Pydantic Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
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

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Extract and validate the current user from the JWT token.
    This uses Supabase's built-in JWT validation.
    """
    try:
        # Get user from Supabase using the token
        response = supabase_client.auth.get_user(credentials.credentials)
        
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return response.user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)) -> UserProfile:
    """
    Get the full user profile including role and school information.
    """
    try:
        # Query the profiles table with school information
        response = supabase_client.table('profiles').select(
            'id, email, first_name, last_name, role, school_id, schools(name)'
        ).eq('id', current_user.id).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        profile_data = response.data
        school_name = profile_data['schools']['name'] if profile_data['schools'] else "Unknown School"
        
        return UserProfile(
            id=profile_data['id'],
            email=profile_data['email'],
            first_name=profile_data['first_name'],
            last_name=profile_data['last_name'],
            role=profile_data['role'],
            school_id=profile_data['school_id'],
            school_name=school_name
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user profile: {str(e)}"
        )

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """
    Authenticate user with email and password using Supabase Auth.
    Returns access token and user profile information.
    """
    try:
        # Authenticate with Supabase
        auth_response = supabase_client.auth.sign_in_with_password({
            "email": login_data.email,
            "password": login_data.password
        })
        
        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = auth_response.user
        session = auth_response.session
        
        # Get user profile information
        profile_response = supabase_client.table('profiles').select(
            'id, email, first_name, last_name, role, school_id, schools(name)'
        ).eq('id', user.id).single().execute()
        
        if not profile_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found. Please contact administrator."
            )
        
        profile_data = profile_response.data
        school_name = profile_data['schools']['name'] if profile_data['schools'] else "Unknown School"
        
        return LoginResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user={
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at
            },
            profile={
                "id": profile_data['id'],
                "email": profile_data['email'],
                "first_name": profile_data['first_name'],
                "last_name": profile_data['last_name'],
                "role": profile_data['role'],
                "school_id": profile_data['school_id'],
                "school_name": school_name
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Logout the current user by invalidating their session.
    """
    try:
        supabase_client.auth.sign_out()
        return {"message": "Successfully logged out"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )

@router.get("/me", response_model=UserProfile)
async def get_current_user_info(current_user_profile: UserProfile = Depends(get_current_user_profile)):
    """
    Get current authenticated user's profile information.
    """
    return current_user_profile

@router.get("/check")
async def check_auth(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Simple endpoint to check if user is authenticated.
    """
    return {
        "authenticated": True,
        "user_id": current_user.id,
        "email": current_user.email
    } 