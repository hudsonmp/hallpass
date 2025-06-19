from .school_schema import School, SchoolCreate, SchoolUpdate
from .profile_schema import Profile, ProfileCreate, ProfileUpdate
from .location_schema import Location, LocationCreate, LocationUpdate
from .pass_schema import Pass, PassCreate, PassApprove, PassComplete
from .auth_schema import Token, TokenPayload, LoginSchema, SignupSchema
from .enums import RoleEnum, PassStatusEnum

__all__ = [
    "School",
    "SchoolCreate",
    "SchoolUpdate",
    "Profile",
    "ProfileCreate",
    "ProfileUpdate",
    "Location",
    "LocationCreate",
    "LocationUpdate",
    "Pass",
    "PassCreate",
    "PassApprove",
    "PassComplete",
    "Token",
    "TokenPayload",
    "LoginSchema",
    "SignupSchema",
    "RoleEnum",
    "PassStatusEnum",
]

# Resolve forward references
School.update_forward_refs(Location=Location, Profile=Profile)
Profile.update_forward_refs(School=School, Pass=Pass)
Location.update_forward_refs(School=School, Pass=Pass)
Pass.update_forward_refs(Profile=Profile, Location=Location) 