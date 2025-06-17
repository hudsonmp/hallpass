# SchoolSecure Backend API v0.0.1

FastAPI backend for the SchoolSecure Hall Pass Management System.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Setup

Copy the example environment file and add your Supabase service role key:

```bash
cp ../.env.example ../.env
```

Edit `.env` and add your **service role key** from Supabase Dashboard > Settings > API:

```env
SUPABASE_SERVICE_ROLE_KEY="your_service_role_key_here"
```

### 3. Seed Test Users

```bash
python run_seeding.py
```

This creates:
- 1 Administrator: `hudsonmitchellpullman+admin@gmail.com`
- 2 Teachers: `hudsonmitchellpullman+teacher1@gmail.com`, `hudsonmitchellpullman+teacher2@gmail.com`
- 10 Students: `hudsonmitchellpullman+student1@gmail.com` through `hudsonmitchellpullman+student10@gmail.com`

**Password for all accounts**: `2010Testing!`

### 4. Start the API Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

### 5. Test the API

```bash
python test_api.py
```

## 📚 API Documentation

Interactive documentation is available at:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## 🔐 Authentication Endpoints

### POST `/api/v1/auth/login`

Authenticate with email and password.

**Request Body**:
```json
{
  "email": "hudsonmitchellpullman+student1@gmail.com",
  "password": "2010Testing!"
}
```

**Response**:
```json
{
  "access_token": "jwt_token_here",
  "refresh_token": "refresh_token_here",
  "user": {...},
  "profile": {
    "id": "uuid",
    "email": "...",
    "first_name": "Alice",
    "last_name": "Johnson",
    "role": "student",
    "school_id": "uuid",
    "school_name": "Edison Elementary School"
  }
}
```

### GET `/api/v1/auth/me`

Get current user profile information.

**Headers**: `Authorization: Bearer <token>`

### POST `/api/v1/auth/logout`

Logout current user.

## 🎫 Pass Management Endpoints

### GET `/api/v1/passes/locations`

Get available hall pass locations for the user's school.

**Headers**: `Authorization: Bearer <token>`

**Response**:
```json
{
  "pre_approved": [
    {
      "id": "uuid",
      "name": "Nurse",
      "description": "School health office",
      "default_duration": 20,
      "requires_approval": false,
      "is_early_release_only": false,
      "is_summons_only": false
    }
  ],
  "requires_approval": [...]
}
```

### POST `/api/v1/passes/`

Create a new hall pass (students only, pre-approved locations only in v0.0.1).

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "location_id": "uuid",
  "student_reason": "Feeling unwell",
  "requested_start_time": "2024-06-16T10:30:00Z",
  "is_summons": false,
  "is_early_release": false
}
```

### GET `/api/v1/passes/`

Get passes based on user role:
- **Students**: Only their own passes
- **Teachers/Admins**: All passes from their school

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `status_filter`: Filter by pass status (optional)
- `limit`: Number of passes to return (default: 50, max: 100)
- `offset`: Number of passes to skip (default: 0)

### GET `/api/v1/passes/{pass_id}`

Get a specific pass by ID.

**Headers**: `Authorization: Bearer <token>`

### PATCH `/api/v1/passes/{pass_id}/activate`

Activate an approved pass (students only). Changes status from 'approved' to 'active' and generates QR code.

**Headers**: `Authorization: Bearer <token>`

## 🏗️ Architecture

### Database Integration

The API uses Supabase as the database with Row Level Security (RLS) policies:

- **Students** can only see/modify their own passes
- **Teachers** can see all passes from their school
- **Administrators** have full access to their school's data

### Authentication Flow

1. User logs in with email/password
2. Supabase validates credentials and returns JWT
3. JWT is used for all subsequent API calls
4. RLS policies automatically filter data based on user role

### Pass Creation Logic

For v0.0.1, only **pre-approved passes** are supported:

1. Student selects a pre-approved location (nurse, counselor when summoned, office when early release)
2. Pass is automatically approved and ready for activation
3. Student can activate the pass to generate QR code
4. Pass tracks actual start/end times for analytics

## 🛡️ Security Features

- **JWT Authentication**: Secure token-based authentication
- **Row Level Security**: Database-level access control
- **Role-based Authorization**: Different permissions per user role
- **Input Validation**: Pydantic models validate all requests
- **CORS Configuration**: Configurable for frontend integration

## 📁 File Structure

```
backend/
├── api/
│   └── v1/
│       ├── auth.py          # Authentication endpoints
│       ├── passes.py        # Pass management endpoints
│       ├── schools.py       # School configuration endpoints
│       └── dashboards.py    # Analytics endpoints
├── core/
│   └── config.py           # Configuration settings
├── db/
│   ├── supabase_client.py  # Database client
│   └── DATABASE_SCHEMA.md  # Database documentation
├── schemas/
│   ├── pass_schema.py      # Pass-related Pydantic models
│   ├── school_schema.py    # School-related models
│   └── dashboard_schema.py # Dashboard models
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── seed_users.py          # User seeding script
├── run_seeding.py         # Seeding wrapper script
└── test_api.py            # API testing script
```

## 🔧 Development

### Running in Development

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Test all endpoints
python test_api.py

# Test specific user role
python -c "
import test_api
token = test_api.test_login('student')
test_api.test_get_locations(token)
"
```

### Adding New Endpoints

1. Create/update Pydantic schemas in `schemas/`
2. Add endpoint logic in appropriate `api/v1/` file
3. Update main.py to include router if needed
4. Test with interactive docs at `/docs`

## 🚨 Common Issues

### Authentication Errors

- Make sure `SUPABASE_SERVICE_ROLE_KEY` is set in `.env`
- Verify users are seeded: `python run_seeding.py`
- Check JWT token format: `Authorization: Bearer <token>`

### Permission Errors

- RLS policies are enforced - students can only see their own data
- Use correct user role for testing
- Check database policies in Supabase dashboard

### Database Connection Issues

- Verify `SUPABASE_URL` is correct
- Check Supabase project is active
- Ensure RLS policies are properly configured

## 📈 Next Steps

1. **Teacher Approval Endpoints**: For approval-required passes
2. **Dashboard Analytics**: Implement analytics calculations
3. **Real-time Updates**: Add WebSocket support for live updates
4. **Advanced Search**: Add filtering and search capabilities
5. **Bulk Operations**: Support for bulk pass operations

## 🤝 Contributing

This backend follows the "backend first" development approach:

1. Design database schema and RLS policies
2. Implement API endpoints with proper authentication
3. Create comprehensive tests
4. Build frontend to consume the API

All endpoints respect the database RLS policies and provide role-based access control. 