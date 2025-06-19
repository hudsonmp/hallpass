from enum import Enum


class RoleEnum(str, Enum):
    student = "student"
    teacher = "teacher"
    administrator = "administrator"


class PassStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    active = "active"
    completed = "completed"
    denied = "denied"
    expired = "expired" 