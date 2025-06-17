# SchoolSecure v0.0.1 Database Schema Documentation

## Overview

This document describes the complete database schema for the SchoolSecure Hall Pass Management System. The database is built on PostgreSQL using Supabase and implements Row Level Security (RLS) for data isolation between different user roles.

## Database Connection Details

- **Project ID**: `rxqlewoujpqyvurzzlfv`
- **Project Name**: Hallpass
- **Test School ID**: `fd29756b-2782-4119-9811-6b61443a09de`
- **Test School Name**: Edison Elementary School

## Table Structure

### 1. Schools Table (`public.schools`)

**Purpose**: Stores school information and configuration settings that administrators can customize.

**Columns**:
- `id` (UUID, Primary Key) - Unique school identifier
- `name` (VARCHAR(255)) - School name
- `created_at` (TIMESTAMPTZ) - Record creation timestamp
- `updated_at` (TIMESTAMPTZ) - Last update timestamp
- `default_pass_duration` (INTEGER) - Default pass duration in minutes (default: 10)
- `concurrent_pass_limit` (INTEGER) - Max students out simultaneously (default: 5)
- `pre_approved_settings` (JSONB) - JSON configuration for pre-approved pass types

**Sample Pre-approved Settings**:
```json
{
  "nurse": {"duration": 20, "requires_approval": false},
  "bathroom": {"duration": 10, "requires_approval": true},
  "water": {"duration": 5, "requires_approval": true},
  "counselor": {"duration": 30, "requires_approval": false, "summons_only": true},
  "office": {"duration": 15, "requires_approval": false, "early_release_only": true}
}
```

### 2. Profiles Table (`public.profiles`)

**Purpose**: Links to Supabase's `auth.users` table and stores application-specific user data.

**Columns**:
- `id` (UUID, Primary Key, Foreign Key to `auth.users.id`) - User identifier
- `school_id` (UUID, Foreign Key to `schools.id`) - Associated school
- `email` (VARCHAR(255), Unique) - User email address
- `first_name` (VARCHAR(100)) - User's first name
- `last_name` (VARCHAR(100)) - User's last name
- `role` (VARCHAR(20)) - User role: 'student', 'teacher', or 'administrator'
- `created_at` (TIMESTAMPTZ) - Record creation timestamp
- `updated_at` (TIMESTAMPTZ) - Last update timestamp
- `student_id` (VARCHAR(50)) - School-assigned student ID (students only)
- `grade_level` (INTEGER) - Student grade level (students only)
- `teacher_id` (VARCHAR(50)) - School-assigned teacher ID (teachers only)
- `department` (VARCHAR(100)) - Teacher department (teachers only)
- `admin_permissions` (JSONB) - Admin permissions array (administrators only)

### 3. Locations Table (`public.locations`)

**Purpose**: Defines available hall pass destinations that can be customized per school.

**Columns**:
- `id` (UUID, Primary Key) - Unique location identifier
- `school_id` (UUID, Foreign Key to `schools.id`) - Associated school
- `name` (VARCHAR(100)) - Location name
- `description` (TEXT) - Location description
- `default_duration` (INTEGER) - Default pass duration for this location (minutes)
- `requires_approval` (BOOLEAN) - Whether passes to this location need teacher approval
- `is_active` (BOOLEAN) - Whether this location is currently available
- `created_at` (TIMESTAMPTZ) - Record creation timestamp
- `is_early_release_only` (BOOLEAN) - Only accessible with early release passes
- `is_summons_only` (BOOLEAN) - Only accessible when summoned
- `room_number` (VARCHAR(20)) - Optional room number

**Default Locations Created**:
1. Bathroom (requires approval, 10 min)
2. Nurse (pre-approved, 20 min)
3. Water Fountain (requires approval, 5 min)
4. Principal Office (summons only, 15 min)
5. Counselor (summons only, 30 min)
6. Front Office (early release only, 15 min)
7. Library (requires approval, 25 min)
8. Other Classroom (requires approval, 20 min)

### 4. Passes Table (`public.passes`)

**Purpose**: Core table tracking all hall pass requests and their complete lifecycle.

**Columns**:
- `id` (UUID, Primary Key) - Unique pass identifier
- `school_id` (UUID, Foreign Key to `schools.id`) - Associated school
- `student_id` (UUID, Foreign Key to `profiles.id`) - Student requesting the pass
- `location_id` (UUID, Foreign Key to `locations.id`) - Destination location
- `created_at` (TIMESTAMPTZ) - Pass creation timestamp
- `updated_at` (TIMESTAMPTZ) - Last update timestamp
- `status` (VARCHAR(20)) - Pass status: 'pending', 'approved', 'active', 'completed', 'denied', 'expired'
- `requested_start_time` (TIMESTAMPTZ) - When student wants to start the pass
- `actual_start_time` (TIMESTAMPTZ) - When pass was actually activated
- `requested_end_time` (TIMESTAMPTZ) - When student expects to return
- `actual_end_time` (TIMESTAMPTZ) - When pass was actually completed
- `duration_minutes` (INTEGER) - Actual duration of the pass
- `approver_id` (UUID, Foreign Key to `profiles.id`) - Teacher/admin who approved
- `approved_at` (TIMESTAMPTZ) - When pass was approved
- `approval_notes` (TEXT) - Notes from approver
- `is_summons` (BOOLEAN) - Whether this is a summons pass
- `is_early_release` (BOOLEAN) - Whether this is an early release pass
- `verification_code` (VARCHAR(50)) - QR code for verification (auto-generated)
- `student_reason` (TEXT) - Student's reason for the pass
- `admin_notes` (TEXT) - Administrative notes

## Database Functions and Triggers

### Automatic Timestamp Updates
- `update_updated_at_column()` - Function that updates the `updated_at` field
- Applied to all tables with `updated_at` columns

### Pass Verification Code Generation
- `generate_verification_code()` - Generates unique QR codes for active passes
- `set_verification_code()` - Trigger that automatically sets verification codes when passes become active
- Also calculates actual duration when passes are completed

## Row Level Security (RLS) Policies

All tables have RLS enabled with the following policies:

### Schools Table Policies
- **View**: Users can only see their own school's data
- **Update**: Only administrators can modify school settings

### Profiles Table Policies
- **View Own**: Users can view their own profile
- **Update Own**: Users can update their own basic profile information
- **View School**: Teachers and administrators can view all profiles from their school

### Locations Table Policies
- **View**: All authenticated users can view locations from their school
- **Manage**: Only administrators can create, update, or delete locations

### Passes Table Policies
- **Student View**: Students can only view their own passes
- **Student Create**: Students can create passes for themselves (approval depends on location)
- **Student Update**: Students can update their own pending passes
- **Teacher View**: Teachers can view all passes from their school
- **Teacher Manage**: Teachers can approve, deny, and create passes for students

## Indexes for Performance

### Schools Table
- `idx_schools_name` - Index on school name

### Profiles Table
- `idx_profiles_school_id` - Index on school association
- `idx_profiles_role` - Index on user role
- `idx_profiles_email` - Index on email address
- `idx_profiles_name` - Composite index on first and last name

### Locations Table
- `idx_locations_school_id` - Index on school association
- `idx_locations_active` - Index on active status

### Passes Table
- `idx_passes_school_id` - Index on school association
- `idx_passes_student_id` - Index on student
- `idx_passes_status` - Index on pass status
- `idx_passes_created_at` - Index on creation time
- `idx_passes_approver_id` - Index on approver
- `idx_passes_location_id` - Index on location
- `idx_passes_school_status` - Composite index for school + status queries
- `idx_passes_student_status` - Composite index for student + status queries

## Data Relationships

```
auth.users (Supabase managed)
    ↓ (1:1)
profiles
    ↓ (N:1)
schools ← locations
    ↓ (1:N)    ↓ (1:N)
    passes ←────┘
```

## Sample Data

The database includes:
- 1 test school: "Edison Elementary School"
- 8 default locations with appropriate approval settings
- Ready for user seeding via the `seed_users.py` script

## Security Features

1. **Row Level Security**: Ensures data isolation between schools and user roles
2. **Foreign Key Constraints**: Maintains data integrity
3. **Check Constraints**: Validates enum values (roles, pass statuses)
4. **Unique Constraints**: Prevents duplicate emails and location names per school
5. **Cascade Deletes**: Properly handles related data when schools or users are deleted

## Next Steps

1. Run the `seed_users.py` script to create test users
2. Implement backend API endpoints that respect the RLS policies
3. Build frontend interfaces that work with the defined data structure

## Database Connection Information

To connect to this database, you'll need:
- `SUPABASE_URL`: Your project's API URL
- `SUPABASE_ANON_KEY`: For client-side operations
- `SUPABASE_SERVICE_ROLE_KEY`: For server-side operations (bypasses RLS)

The project ID `rxqlewoujpqyvurzzlfv` should be used for all Supabase MCP operations. 