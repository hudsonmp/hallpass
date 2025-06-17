-- ============================================================================
-- SchoolSecure v0.0.1 Database Schema
-- Hall Pass Management System for K-12 Schools
-- ============================================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. SCHOOLS TABLE
-- Stores school information and configuration settings
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.schools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Configuration settings (can be overridden by administrators)
    default_pass_duration INTEGER DEFAULT 10, -- minutes
    concurrent_pass_limit INTEGER DEFAULT 5, -- max students out at once
    
    -- JSON field for pre-approved pass settings
    pre_approved_settings JSONB DEFAULT '{
        "nurse": {"duration": 20, "requires_approval": false},
        "bathroom": {"duration": 10, "requires_approval": true},
        "water": {"duration": 5, "requires_approval": true},
        "counselor": {"duration": 30, "requires_approval": false, "summons_only": true},
        "office": {"duration": 15, "requires_approval": false, "early_release_only": true}
    }'::jsonb
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_schools_name ON public.schools(name);

-- ============================================================================
-- 2. PROFILES TABLE  
-- Links to auth.users and stores app-specific user data
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    school_id UUID NOT NULL REFERENCES public.schools(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('student', 'teacher', 'administrator')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Student-specific fields
    student_id VARCHAR(50), -- school-assigned student ID
    grade_level INTEGER,
    
    -- Teacher-specific fields  
    teacher_id VARCHAR(50), -- school-assigned teacher ID
    department VARCHAR(100),
    
    -- Admin-specific fields
    admin_permissions JSONB DEFAULT '["manage_school", "manage_users", "view_all_passes"]'::jsonb
);

-- Add indexes for performance and lookups
CREATE INDEX IF NOT EXISTS idx_profiles_school_id ON public.profiles(school_id);
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_name ON public.profiles(first_name, last_name);

-- ============================================================================
-- 3. LOCATIONS TABLE
-- Pass destinations that can be customized per school
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID NOT NULL REFERENCES public.schools(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    default_duration INTEGER DEFAULT 10, -- minutes
    requires_approval BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Special location types
    is_early_release_only BOOLEAN DEFAULT false,
    is_summons_only BOOLEAN DEFAULT false,
    room_number VARCHAR(20),
    
    UNIQUE(school_id, name) -- Each school can have unique location names
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_locations_school_id ON public.locations(school_id);
CREATE INDEX IF NOT EXISTS idx_locations_active ON public.locations(is_active);

-- ============================================================================
-- 4. PASSES TABLE
-- Core table tracking all hall pass requests and their lifecycle
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.passes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID NOT NULL REFERENCES public.schools(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES public.locations(id) ON DELETE RESTRICT,
    
    -- Pass metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Pass status and timing
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'approved', 'active', 'completed', 'denied', 'expired')
    ),
    
    -- Time tracking
    requested_start_time TIMESTAMP WITH TIME ZONE,
    actual_start_time TIMESTAMP WITH TIME ZONE,
    requested_end_time TIMESTAMP WITH TIME ZONE,
    actual_end_time TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    
    -- Approval tracking
    approver_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    approval_notes TEXT,
    
    -- Special pass types
    is_summons BOOLEAN DEFAULT false,
    is_early_release BOOLEAN DEFAULT false,
    
    -- QR code for verification (generated when pass becomes active)
    verification_code VARCHAR(50),
    
    -- Notes and reason
    student_reason TEXT,
    admin_notes TEXT
);

-- Add comprehensive indexes for queries
CREATE INDEX IF NOT EXISTS idx_passes_school_id ON public.passes(school_id);
CREATE INDEX IF NOT EXISTS idx_passes_student_id ON public.passes(student_id);
CREATE INDEX IF NOT EXISTS idx_passes_status ON public.passes(status);
CREATE INDEX IF NOT EXISTS idx_passes_created_at ON public.passes(created_at);
CREATE INDEX IF NOT EXISTS idx_passes_approver_id ON public.passes(approver_id);
CREATE INDEX IF NOT EXISTS idx_passes_location_id ON public.passes(location_id);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_passes_school_status ON public.passes(school_id, status);
CREATE INDEX IF NOT EXISTS idx_passes_student_status ON public.passes(student_id, status);

-- ============================================================================
-- 5. TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_schools_updated_at 
    BEFORE UPDATE ON public.schools 
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_profiles_updated_at 
    BEFORE UPDATE ON public.profiles 
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column(); 

CREATE TRIGGER update_passes_updated_at 
    BEFORE UPDATE ON public.passes 
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================================
-- 6. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.schools ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;  
ALTER TABLE public.locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.passes ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- SCHOOLS TABLE POLICIES
-- ============================================================================

-- Users can only see their own school
CREATE POLICY "Users can view their own school" ON public.schools
    FOR SELECT USING (
        id IN (
            SELECT school_id FROM public.profiles 
            WHERE id = auth.uid()
        )
    );

-- Only administrators can update school settings
CREATE POLICY "Administrators can update school settings" ON public.schools
    FOR UPDATE USING (
        id IN (
            SELECT school_id FROM public.profiles 
            WHERE id = auth.uid() AND role = 'administrator'
        )
    );

-- ============================================================================
-- PROFILES TABLE POLICIES  
-- ============================================================================

-- Users can view their own profile
CREATE POLICY "Users can view own profile" ON public.profiles
    FOR SELECT USING (id = auth.uid());

-- Users can update their own basic profile info
CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (id = auth.uid());

-- Teachers and admins can view profiles from their school
CREATE POLICY "Teachers and admins can view school profiles" ON public.profiles
    FOR SELECT USING (
        school_id IN (
            SELECT school_id FROM public.profiles 
            WHERE id = auth.uid() AND role IN ('teacher', 'administrator')
        )
    );

-- ============================================================================
-- LOCATIONS TABLE POLICIES
-- ============================================================================

-- All authenticated users can view locations from their school
CREATE POLICY "Users can view school locations" ON public.locations
    FOR SELECT USING (
        school_id IN (
            SELECT school_id FROM public.profiles 
            WHERE id = auth.uid()
        )
    );

-- Only administrators can manage locations
CREATE POLICY "Administrators can manage locations" ON public.locations
    FOR ALL USING (
        school_id IN (
            SELECT school_id FROM public.profiles 
            WHERE id = auth.uid() AND role = 'administrator'
        )
    );

-- ============================================================================
-- PASSES TABLE POLICIES
-- ============================================================================

-- Students can view their own passes
CREATE POLICY "Students can view own passes" ON public.passes
    FOR SELECT USING (student_id = auth.uid());

-- Students can create passes (but approval depends on location settings)
CREATE POLICY "Students can create passes" ON public.passes
    FOR INSERT WITH CHECK (
        student_id = auth.uid() AND
        school_id IN (
            SELECT school_id FROM public.profiles 
            WHERE id = auth.uid()
        )
    );

-- Students can update their own pending passes
CREATE POLICY "Students can update own pending passes" ON public.passes
    FOR UPDATE USING (
        student_id = auth.uid() AND status = 'pending'
    );

-- Teachers can view passes from their school
CREATE POLICY "Teachers can view school passes" ON public.passes
    FOR SELECT USING (
        school_id IN (
            SELECT school_id FROM public.profiles 
            WHERE id = auth.uid() AND role IN ('teacher', 'administrator')
        )
    );

-- Teachers can approve/deny passes and create passes for students
CREATE POLICY "Teachers can manage passes" ON public.passes
    FOR ALL USING (
        school_id IN (
            SELECT school_id FROM public.profiles 
            WHERE id = auth.uid() AND role IN ('teacher', 'administrator')
        )
    );

-- ============================================================================
-- 7. FUNCTIONS FOR BUSINESS LOGIC
-- ============================================================================

-- Function to generate verification code for active passes
CREATE OR REPLACE FUNCTION public.generate_verification_code()
RETURNS TEXT AS $$
BEGIN
    RETURN 'QR-' || UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 8));
END;
$$ LANGUAGE plpgsql;

-- Function to automatically set verification code when pass becomes active
CREATE OR REPLACE FUNCTION public.set_verification_code()
RETURNS TRIGGER AS $$
BEGIN
    -- If status is changing to 'active' and no verification code exists
    IF NEW.status = 'active' AND (OLD.status != 'active' OR OLD.verification_code IS NULL) THEN
        NEW.verification_code = public.generate_verification_code();
        NEW.actual_start_time = NOW();
    END IF;
    
    -- If status is changing to 'completed', set actual_end_time
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        NEW.actual_end_time = NOW();
        -- Calculate actual duration
        IF NEW.actual_start_time IS NOT NULL THEN
            NEW.duration_minutes = EXTRACT(EPOCH FROM (NEW.actual_end_time - NEW.actual_start_time)) / 60;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to passes table
CREATE TRIGGER set_pass_verification_code 
    BEFORE UPDATE ON public.passes
    FOR EACH ROW EXECUTE FUNCTION public.set_verification_code();

-- ============================================================================
-- 8. SAMPLE SCHOOL DATA
-- ============================================================================

-- Insert the test school (this will be used by the seed script)
INSERT INTO public.schools (id, name) 
VALUES (
    'fd29756b-2782-4119-9811-6b61443a09de'::uuid,
    'Edison Elementary School'
) 
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 9. DEFAULT LOCATIONS FOR TEST SCHOOL
-- ============================================================================

-- Insert default locations for the test school
INSERT INTO public.locations (school_id, name, description, default_duration, requires_approval, is_early_release_only, is_summons_only) VALUES
    ('fd29756b-2782-4119-9811-6b61443a09de'::uuid, 'Bathroom', 'Student restroom', 10, true, false, false),
    ('fd29756b-2782-4119-9811-6b61443a09de'::uuid, 'Nurse', 'School health office', 20, false, false, false),
    ('fd29756b-2782-4119-9811-6b61443a09de'::uuid, 'Water Fountain', 'Get a drink of water', 5, true, false, false),
    ('fd29756b-2782-4119-9811-6b61443a09de'::uuid, 'Principal Office', 'Administrative office', 15, false, false, true),
    ('fd29756b-2782-4119-9811-6b61443a09de'::uuid, 'Counselor', 'Student counseling services', 30, false, false, true),
    ('fd29756b-2782-4119-9811-6b61443a09de'::uuid, 'Front Office', 'Main school office', 15, false, true, false),
    ('fd29756b-2782-4119-9811-6b61443a09de'::uuid, 'Library', 'School library/media center', 25, true, false, false),
    ('fd29756b-2782-4119-9811-6b61443a09de'::uuid, 'Other Classroom', 'Visit another classroom', 20, true, false, false)
ON CONFLICT (school_id, name) DO NOTHING;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

-- Grant necessary permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated; 