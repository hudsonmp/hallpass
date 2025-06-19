# SchoolSecure Backend - Role-Based Authentication System

## Overview

This is the backend implementation for SchoolSecure v0.0.1, a comprehensive hall pass management system for K-12 schools. The system implements robust role-based authentication and authorization using FastAPI and Supabase.

## Architecture

### Technology Stack
- **Framework**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL with RLS)
- **Authentication**: Supabase Auth + JWT
- **Authorization**: Role-based access control (RBAC)

### User Roles
1. **Students**: Can create pass requests, view their own passes, activate approved passes
2. **Teachers**: Can approve/deny requests, issue passes directly, view school passes
3. **Administrators**: Can manage all passes, view analytics, configure school settings

## Features Implemented

### ✅ Authentication System
- **JWT-based authentication** using Supabase Auth
- **Dual client setup**: Anon client for auth, Service client for backend operations
- **Token refresh** mechanism for seamless user experience
- **Role-based dependencies** for endpoint protection
- **Hierarchical permissions** (admins can access teacher endpoints)

### ✅ Pass Management
- **Student pass requests** with automatic approval for pre-configured locations
- **Teacher pass approval** workflow with notifications
- **Direct pass issuance** by teachers/admins for summons and early release
- **QR code generation** for active passes
- **Pass lifecycle tracking** (pending → approved → active → completed)

### ✅ Analytics & Dashboards
- **Teacher dashboard**: Personal metrics vs. school averages
- **Admin dashboard**: School-wide analytics and peak usage times
- **Graceful data handling**: "Not Enough Data" when metrics unavailable

### ✅ Security Features
- **Row Level Security (RLS)** policies on all tables
- **Service role isolation** for backend operations
- **CORS configuration** for frontend integration
- **Input validation** with Pydantic models

## API Endpoints

### Authentication (`/api/v1/auth`)
```http
POST   /login              # User login
POST   /refresh            # Token refresh
POST   /logout             # User logout
GET    /me                 # Current user info
GET    /check              # Auth status check

# Demo role endpoints
GET    /student-only       # Students only
GET    /teacher-only       # Teachers and admins
GET    /admin-only         # Administrators only
```

### Pass Management (`/api/v1/passes`)
```http
# Student endpoints
POST   /request            # Request a new pass
GET    /mine               # Get my passes
POST   /{id}/activate      # Activate approved pass

# Teacher endpoints  
POST   /issue              # Issue pass directly to student
GET    /pending            # Get pending approvals
PUT    /{id}/approve       # Approve/deny pass
GET    /school             # View all school passes

# Shared endpoints
GET    /{id}               # Get specific pass details
```

### Dashboards (`/api/v1/dashboards`)
```http
GET    /                   # Role-appropriate dashboard
GET    /teacher            # Teacher analytics
GET    /admin              # Administrator analytics
```

## Database Schema

### Core Tables
- **schools**: School configuration and settings
- **profiles**: User profiles with role information
- **locations**: Available pass destinations
- **passes**: Hall pass requests and lifecycle

### Key Features
- **UUIDs** for all primary keys
- **Timestamps** with automatic updates
- **JSON fields** for flexible configuration
- **Foreign key constraints** for data integrity
- **Comprehensive indexing** for performance

## Security Implementation

### Row Level Security Policies

**Schools Table**:
- Users can only see their own school
- Only admins can modify school settings

**Profiles Table**:
- Users can view/update their own profile
- Teachers/admins can view school profiles

**Passes Table**:
- Students can only see their own passes
- Teachers/admins can see all school passes
- Students can only create passes for themselves

### JWT Token Validation
```python
# Every protected endpoint validates JWT through Supabase
user = supabase_admin.auth.get_user(token)
```

### Role-Based Dependencies
```python
# Reusable authorization dependencies
require_student = require_role(["student"])
require_teacher = require_role(["teacher", "administrator"])
require_admin = require_role(["administrator"])
```

## Setup Instructions

### 1. Environment Configuration
```bash
cp .env.example .env
# Fill in your Supabase credentials
```

### 2. Database Setup
```bash
# Run the schema in your Supabase SQL editor
cat backend/db/schema.sql
```

### 3. Seed Test Data
```bash
python backend/seed_users.py
```

### 4. Start Development Server
```bash
uvicorn backend.main:app --reload
```

### 5. Test Authentication
```bash
python backend/test_auth.py
```

## Configuration

### Required Environment Variables
```env
SUPABASE_URL=your-project-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key
```

### Pre-seeded Test Users
- **Admin**: `hudsonmitchellpullman+admin@gmail.com`
- **Teacher**: `hudsonmitchellpullman+teacher1@gmail.com`
- **Student**: `hudsonmitchellpullman+student1@gmail.com`
- **Password**: `2010Testing!` (for all users)

## API Response Examples

### Login Response
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "role": "student",
    "first_name": "John",
    "last_name": "Doe",
    "school_id": "uuid",
    "school_name": "Edison Elementary School"
  }
}
```

### Pass Response
```json
{
  "id": "uuid",
  "student_id": "uuid", 
  "student_name": "John Doe",
  "location_id": "uuid",
  "location_name": "Nurse",
  "status": "approved",
  "created_at": "2024-01-15T10:30:00Z",
  "verification_code": "QR-ABC123XY",
  "duration_minutes": 20,
  "is_summons": false,
  "is_early_release": false
}
```

### Dashboard Response (Teacher)
```json
{
  "user_role": "teacher",
  "metrics": {
    "passes_granted_week": 15,
    "passes_granted_month": 67,
    "avg_absence_duration": 12.5,
    "school_avg_passes_week": 18.2,
    "school_avg_passes_month": 73.1,
    "school_avg_absence_duration": 14.1,
    "data_available": true
  }
}
```

## Testing

The system includes comprehensive test coverage:

### Authentication Tests
- ✅ User login for all roles
- ✅ JWT token validation  
- ✅ Token refresh mechanism
- ✅ Role-based endpoint access

### Authorization Tests
- ✅ Student-only endpoints
- ✅ Teacher-only endpoints
- ✅ Admin-only endpoints
- ✅ Hierarchical access (admins → teacher endpoints)

### Run Tests
```bash
python backend/test_auth.py
```

## Error Handling

### HTTP Status Codes
- **200**: Success
- **400**: Bad Request (validation errors)
- **401**: Unauthorized (invalid/missing token)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found
- **500**: Internal Server Error

### Example Error Response
```json
{
  "detail": "Forbidden: requires role ['teacher', 'administrator'], but user has role 'student'"
}
```

## Performance Considerations

### Database Optimization
- **Indexes** on frequently queried columns
- **Composite indexes** for complex queries
- **RLS policies** optimized for performance

### Caching Strategy
- JWT validation cached by Supabase
- Database connections pooled automatically
- Static configuration cached in memory

## Security Best Practices

### ✅ Implemented
- JWT tokens with expiration
- Service role key never exposed to client
- RLS policies as safety net
- Input validation on all endpoints
- CORS configuration
- Password requirements enforced

### Future Enhancements
- Rate limiting on auth endpoints
- Audit logging for sensitive operations
- Additional password complexity requirements
- Session management and concurrent login limits

## Development Notes

### Code Organization
```
backend/
├── api/v1/           # API route handlers
├── core/             # Configuration and settings
├── db/               # Database schema and client
├── schemas/          # Pydantic models (legacy)
├── main.py           # FastAPI application
└── requirements.txt  # Python dependencies
```

### Key Dependencies
- `fastapi`: Web framework
- `supabase`: Database and auth client
- `pydantic`: Data validation
- `uvicorn`: ASGI server
- `python-dotenv`: Environment management

## Next Steps

This backend implementation provides a solid foundation for the SchoolSecure v0.0.1 hall pass system. The authentication and authorization framework is production-ready and can be extended for future features such as:

1. **Frontend Integration**: React Native app with proper token handling
2. **Real-time Features**: WebSocket connections for live pass updates
3. **Advanced Analytics**: More detailed reporting and insights
4. **Multi-school Support**: Enhanced tenant isolation
5. **Mobile Notifications**: Push notifications for pass updates

The system is designed to be scalable, secure, and maintainable, following FastAPI and Supabase best practices. 