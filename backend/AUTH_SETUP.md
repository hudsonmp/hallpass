# SchoolSecure Authentication System Setup Guide

This guide covers the comprehensive role-based authentication system implemented for SchoolSecure's backend API.

## 🏗️ System Architecture

The authentication system uses **Supabase Auth + FastAPI** with the following components:

- **Supabase Auth**: Handles user authentication, JWT tokens, and session management
- **FastAPI Dependencies**: Role-based authorization and endpoint protection
- **Row Level Security (RLS)**: Database-level access control
- **JWT Tokens**: Secure, stateless authentication with refresh capability

## 🔑 Authentication Flow

### 1. Login Process
```
Client -> POST /api/v1/auth/login -> Supabase Auth -> JWT + Refresh Token -> Client
```

### 2. Protected Request Flow
```
Client -> Authorization: Bearer <token> -> FastAPI Middleware -> Role Check -> Database Query -> Response
```

### 3. Token Refresh Flow
```
Client -> POST /api/v1/auth/refresh -> Supabase Auth -> New JWT + Refresh Token -> Client
```

## 🛠️ Setup Instructions

### 1. Environment Configuration

Copy `.env.example` to `.env` and configure your Supabase credentials:

```bash
cp .env.example .env
```

Required environment variables:
```env
SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_ANON_KEY="your-supabase-anon-public-key"
SUPABASE_SERVICE_ROLE_KEY="your-supabase-service-role-key"
```

### 2. Supabase Configuration

#### Disable Public Signups
In your Supabase dashboard:
1. Go to **Authentication > Settings**
2. Set **"Allow new users to sign up"** = **False**
3. Set **"Enable email confirmations"** = **False**

This ensures only pre-seeded users can authenticate.

#### Database Setup
The authentication system requires:
- `profiles` table with user roles and school associations
- Row Level Security (RLS) policies on all tables
- Database triggers for automated profile creation

Run the schema from `backend/db/schema.sql` to set up the database structure.

### 3. User Seeding

Pre-seed users using the provided script:

```bash
cd backend
python seed_users.py
```

This creates test users with the following credentials:
- **Admin**: `hudsonmitchellpullman+admin@gmail.com` / `2010Testing!`
- **Teachers**: `hudsonmitchellpullman+teacher1@gmail.com` / `2010Testing!`
- **Students**: `hudsonmitchellpullman+student1@gmail.com` / `2010Testing!`

## 🔐 API Endpoints

### Authentication Endpoints

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "email": "user@example.com",
    "role": "student"
  }
}
```

#### Refresh Token
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

#### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer eyJ...
```

#### Check Authentication
```http
GET /api/v1/auth/check
Authorization: Bearer eyJ...
```

#### Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer eyJ...
```

## 🛡️ Role-Based Access Control

### Role Hierarchy
- **Administrator**: Full access to all endpoints
- **Teacher**: Can manage passes, view dashboards, access student data
- **Student**: Can create pass requests, view own data only

### Endpoint Protection

#### Student-Only Endpoints
```python
@router.post("/passes/request")
async def request_pass(current_user: Dict[str, Any] = Depends(require_student_role)):
    # Only students can access this endpoint
```

#### Teacher/Admin Endpoints
```python
@router.post("/passes/issue") 
async def issue_pass(current_user: Dict[str, Any] = Depends(require_teacher_role)):
    # Teachers and admins can access this endpoint
```

#### Admin-Only Endpoints
```python
@router.get("/dashboard/admin")
async def get_admin_dashboard(current_user: Dict[str, Any] = Depends(require_admin_role)):
    # Only administrators can access this endpoint
```

### Permission Matrix

| Endpoint | Student | Teacher | Admin |
|----------|---------|---------|-------|
| `POST /auth/login` | ✅ | ✅ | ✅ |
| `GET /auth/me` | ✅ | ✅ | ✅ |
| `POST /passes/request` | ✅ | ❌ | ❌ |
| `POST /passes/issue` | ❌ | ✅ | ✅ |
| `PATCH /passes/{id}/approve` | ❌ | ✅ | ✅ |
| `GET /dashboard/student` | ✅ | ❌ | ❌ |
| `GET /dashboard/teacher` | ❌ | ✅ | ✅ |
| `GET /dashboard/admin` | ❌ | ❌ | ✅ |
| `PATCH /schools/me` | ❌ | ❌ | ✅ |

## 🔒 Security Features

### JWT Token Security
- **Access tokens** expire in 60 minutes
- **Refresh tokens** expire in 7 days
- **Single-use refresh tokens** (new refresh token issued on each refresh)
- **Secure HTTP-only cookie storage** (recommended for production)

### Row Level Security (RLS)
Database policies ensure users can only access authorized data:

```sql
-- Students can only view their own passes
CREATE POLICY "Students can view own passes" ON public.passes
    FOR SELECT USING (student_id = auth.uid());

-- Teachers can view all passes from their school
CREATE POLICY "Teachers can view school passes" ON public.passes
    FOR SELECT USING (
        school_id IN (
            SELECT school_id FROM public.profiles 
            WHERE id = auth.uid() AND role IN ('teacher', 'administrator')
        )
    );
```

### Hierarchical Authorization
Administrators automatically inherit all teacher and student permissions:

```python
def require_role(required_roles: List[str]):
    def _role_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_role = current_user["role"]
        
        # Admins have all permissions
        if user_role == "administrator":
            return current_user
            
        # Check specific role requirements
        if user_role not in required_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        return current_user
    return _role_dependency
```

## 🧪 Testing the System

### Manual Testing

1. **Start the backend server:**
```bash
cd backend
uvicorn main:app --reload
```

2. **Run the test suite:**
```bash
python test_auth_system.py
```

### Example Test Cases

#### Login Test
```python
import requests

# Test login
response = requests.post("http://127.0.0.1:8000/api/v1/auth/login", json={
    "email": "hudsonmitchellpullman+admin@gmail.com",
    "password": "2010Testing!"
})

tokens = response.json()
access_token = tokens["access_token"]
```

#### Protected Endpoint Test
```python
# Test protected endpoint
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("http://127.0.0.1:8000/api/v1/auth/me", headers=headers)
user_info = response.json()
```

#### Role-Based Access Test
```python
# Admin accessing admin dashboard (should work)
response = requests.get("http://127.0.0.1:8000/api/v1/dashboard/admin", headers=headers)
assert response.status_code == 200

# Student accessing admin dashboard (should fail)
# ... login as student and try same endpoint
assert response.status_code == 403
```

## 🚨 Error Handling

### Authentication Errors

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | Bad Request | Invalid login credentials |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Insufficient role permissions |
| 422 | Validation Error | Malformed request data |

### Example Error Responses

**Invalid credentials:**
```json
{
  "detail": "Invalid email or password"
}
```

**Insufficient permissions:**
```json
{
  "detail": "Forbidden: requires role ['administrator'], but user has role 'student'"
}
```

**Invalid token:**
```json
{
  "detail": "Invalid or expired token"
}
```

## 🔧 Implementation Details

### Supabase Client Configuration

The system uses two Supabase clients:

```python
# Anon client for authentication operations
supabase_anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Service role client for backend operations  
supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
```

### Dependencies Usage

```python
from backend.core.auth import (
    get_current_user,           # Basic authentication
    require_student_role,       # Student-only access
    require_teacher_role,       # Teacher + Admin access
    require_admin_role,         # Admin-only access
    get_current_user_profile    # Full profile information
)

# Basic authentication
@router.get("/protected")
async def protected_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {"user_id": current_user["id"], "role": current_user["role"]}

# Role-specific access
@router.post("/admin-only")
async def admin_endpoint(current_user: Dict[str, Any] = Depends(require_admin_role)):
    return {"message": "Admin access granted"}
```

## 📝 Best Practices

### Token Storage (Frontend)
- Store access tokens in memory (JavaScript variables)
- Store refresh tokens in secure HTTP-only cookies
- Implement automatic token refresh before expiration
- Clear all tokens on logout

### Error Handling
- Always check token validity before making requests
- Implement proper 401/403 error handling
- Provide clear error messages to users
- Log authentication failures for security monitoring

### Security Considerations
- Use HTTPS in production
- Implement rate limiting on auth endpoints
- Monitor for suspicious authentication patterns
- Regularly rotate service role keys
- Keep Supabase and dependencies updated

## 🤝 Contributing

When adding new protected endpoints:

1. **Choose appropriate dependency:**
   - `get_current_user` - Any authenticated user
   - `require_student_role` - Students only
   - `require_teacher_role` - Teachers and admins
   - `require_admin_role` - Admins only

2. **Implement permission checks:**
   ```python
   # Additional authorization logic if needed
   if current_user["school_id"] != target_school_id:
       raise HTTPException(status_code=403, detail="Access denied")
   ```

3. **Update RLS policies:**
   ```sql
   -- Add database policies for new tables
   CREATE POLICY "policy_name" ON table_name
       FOR operation USING (permission_logic);
   ```

4. **Add tests:**
   - Test authorized access
   - Test unauthorized access
   - Test edge cases

This authentication system provides a robust, scalable foundation for SchoolSecure's security requirements while maintaining ease of use and clear separation of concerns.