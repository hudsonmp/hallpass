#!/usr/bin/env python3
"""
Complete Supabase User Seeding Script for EdTech Hall Pass System
Creates 1 admin, 2 teachers, and 10 students for testing purposes.

Requirements:
- pip install supabase python-dotenv
- .env file with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
- Replace 'youremail' in email addresses with your actual Gmail address
"""

import os
import sys
from typing import List, Dict, Tuple
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ Error: supabase package not installed")
    print("Run: pip install supabase python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Your existing test school ID
TEST_SCHOOL_ID = "fd29756b-2782-4119-9811-6b61443a09de"

# Email configuration for hudsonmitchellpullman@gmail.com
YOUR_EMAIL_PREFIX = "hudsonmitchellpullman"

# User data to create - all using the same password for simplicity
USERS_TO_CREATE = [
    # Administrator
    {
        "email": f"{YOUR_EMAIL_PREFIX}+admin@gmail.com",
        "password": "2010Testing!",
        "role": "administrator",
        "first_name": "Admin",
        "last_name": "User"
    },
    # Teachers
    {
        "email": f"{YOUR_EMAIL_PREFIX}+teacher1@gmail.com", 
        "password": "2010Testing!",
        "role": "teacher",
        "first_name": "Jane",
        "last_name": "Smith"
    },
    {
        "email": f"{YOUR_EMAIL_PREFIX}+teacher2@gmail.com",
        "password": "2010Testing!", 
        "role": "teacher",
        "first_name": "John",
        "last_name": "Davis"
    },
    # Students
    {
        "email": f"{YOUR_EMAIL_PREFIX}+student1@gmail.com",
        "password": "2010Testing!",
        "role": "student", 
        "first_name": "Alice",
        "last_name": "Johnson"
    },
    {
        "email": f"{YOUR_EMAIL_PREFIX}+student2@gmail.com",
        "password": "2010Testing!",
        "role": "student",
        "first_name": "Bob", 
        "last_name": "Wilson"
    },
    {
        "email": f"{YOUR_EMAIL_PREFIX}+student3@gmail.com",
        "password": "2010Testing!",
        "role": "student",
        "first_name": "Carol",
        "last_name": "Brown"
    },
    {
        "email": f"{YOUR_EMAIL_PREFIX}+student4@gmail.com", 
        "password": "2010Testing!",
        "role": "student",
        "first_name": "David",
        "last_name": "Miller"
    },
    {
        "email": f"{YOUR_EMAIL_PREFIX}+student5@gmail.com",
        "password": "2010Testing!",
        "role": "student",
        "first_name": "Emma",
        "last_name": "Garcia"
    },
    {
        "email": f"{YOUR_EMAIL_PREFIX}+student6@gmail.com",
        "password": "2010Testing!", 
        "role": "student",
        "first_name": "Frank",
        "last_name": "Martinez"
    },
    {
        "email": f"{YOUR_EMAIL_PREFIX}+student7@gmail.com",
        "password": "2010Testing!",
        "role": "student",
        "first_name": "Grace",
        "last_name": "Anderson"
    },
    {
        "email": f"{YOUR_EMAIL_PREFIX}+student8@gmail.com",
        "password": "2010Testing!",
        "role": "student", 
        "first_name": "Henry",
        "last_name": "Taylor"
    },
    {
        "email": f"{YOUR_EMAIL_PREFIX}+student9@gmail.com",
        "password": "2010Testing!",
        "role": "student",
        "first_name": "Ivy",
        "last_name": "Thomas"
    },
    {
        "email": f"{YOUR_EMAIL_PREFIX}+student10@gmail.com",
        "password": "2010Testing!",
        "role": "student",
        "first_name": "Jack",
        "last_name": "White"
    }
]

def validate_environment() -> bool:
    """Validate that all required environment variables are set."""
    if not SUPABASE_URL:
        print("❌ Error: SUPABASE_URL not found in environment variables")
        print("Add SUPABASE_URL=https://your-project-id.supabase.co to your .env file")
        return False
    
    if not SUPABASE_SERVICE_ROLE_KEY:
        print("❌ Error: SUPABASE_SERVICE_ROLE_KEY not found in environment variables") 
        print("Add your service role key to your .env file")
        return False
    
    return True

def create_supabase_client() -> Client:
    """Create Supabase client with service role key for admin operations."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def verify_school_exists(supabase: Client) -> bool:
    """Verify that the test school exists in the database."""
    try:
        response = supabase.table('schools').select('id, name').eq('id', TEST_SCHOOL_ID).execute()
        if response.data and len(response.data) > 0:
            school_name = response.data[0]['name']
            print(f"✅ Found test school: {school_name} (ID: {TEST_SCHOOL_ID})")
            return True
        else:
            print(f"❌ Test school with ID {TEST_SCHOOL_ID} not found")
            print("Make sure the school has been created first")
            return False
    except Exception as e:
        print(f"❌ Error verifying school: {str(e)}")
        return False

def check_existing_users(supabase: Client) -> List[str]:
    """Check which users already exist to avoid duplicates."""
    existing_emails = []
    emails_to_check = [user['email'] for user in USERS_TO_CREATE]
    
    try:
        # Check profiles table for existing emails
        response = supabase.table('profiles').select('email').in_('email', emails_to_check).execute()
        if response.data:
            existing_emails = [profile['email'] for profile in response.data]
            
        if existing_emails:
            print(f"⚠️  Found {len(existing_emails)} existing users:")
            for email in existing_emails:
                print(f"   • {email}")
            print()
            
    except Exception as e:
        print(f"⚠️  Could not check existing users: {str(e)}")
        
    return existing_emails

def create_user_and_profile(supabase: Client, user_data: Dict, skip_existing: bool = True) -> Tuple[bool, str]:
    """
    Create a user in auth.users and corresponding profile in profiles table.
    Returns (success: bool, message: str)
    """
    email = user_data['email']
    role = user_data['role']
    
    try:
        print(f"Creating {role}: {email}")
        
        # Step 1: Create user in auth.users using Admin API
        auth_response = supabase.auth.admin.create_user({
            "email": email,
            "password": user_data["password"],
            "email_confirm": True,  # Skip email verification for testing
            "user_metadata": {
                "role": role,
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "test_user": True  # Flag to identify test users
            }
        })
        
        if not auth_response.user:
            return False, f"Failed to create auth user for {email}"
            
        user_id = auth_response.user.id
        print(f"   ✅ Created auth user (ID: {user_id[:8]}...)")
        
        # Step 2: Create profile in profiles table
        profile_data = {
            "id": user_id,
            "school_id": TEST_SCHOOL_ID,
            "email": email,
            "first_name": user_data["first_name"], 
            "last_name": user_data["last_name"],
            "role": role
        }
        
        profile_response = supabase.table('profiles').insert(profile_data).execute()
        
        if profile_response.data:
            print(f"   ✅ Created profile for {email}")
            return True, "Success"
        else:
            return False, f"Failed to create profile for {email}"
            
    except Exception as e:
        error_msg = str(e).lower()
        if "already registered" in error_msg or "already exists" in error_msg:
            if skip_existing:
                print(f"   ⚠️  User {email} already exists, skipping...")
                return True, "Already exists"
            else:
                return False, f"User {email} already exists"
        else:
            return False, f"Error creating user {email}: {str(e)}"

def print_login_credentials(successful_users: List[Dict]):
    """Print login credentials for successfully created users."""
    if not successful_users:
        return
        
    print("\n" + "="*60)
    print("🔑 LOGIN CREDENTIALS FOR TESTING")
    print("="*60)
    
    # Group by role
    roles = {"administrator": [], "teacher": [], "student": []}
    for user in successful_users:
        roles[user["role"]].append(user)
    
    for role, users in roles.items():
        if users:
            print(f"\n{role.upper()}S:")
            for user in users:
                print(f"   📧 {user['email']}")
                print(f"   🔒 {user['password']}")
                print()

def main():
    """Main function to seed all users."""
    print("🚀 EdTech Hall Pass System - User Seeding Script")
    print("="*55)
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    # Initialize Supabase client
    try:
        supabase = create_supabase_client()
        print("✅ Connected to Supabase successfully")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {str(e)}")
        print("Check your SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    
    # Verify school exists
    if not verify_school_exists(supabase):
        print("\n💡 Make sure to create the test school first before running this script")
        sys.exit(1)
    
    # Check for existing users
    existing_users = check_existing_users(supabase)
    
    # Create users and profiles
    print(f"📝 Creating {len(USERS_TO_CREATE)} users...\n")
    
    successful_users = []
    failed_users = []
    skipped_users = []
    
    for user_data in USERS_TO_CREATE:
        if user_data['email'] in existing_users:
            print(f"Skipping {user_data['role']}: {user_data['email']} (already exists)")
            skipped_users.append(user_data)
            continue
            
        success, message = create_user_and_profile(supabase, user_data)
        
        if success:
            successful_users.append(user_data)
        else:
            failed_users.append((user_data, message))
            print(f"   ❌ {message}")
        
        print()  # Add spacing between users
    
    # Print summary
    total = len(USERS_TO_CREATE)
    successful = len(successful_users)
    failed = len(failed_users)
    skipped = len(skipped_users)
    
    print("="*60)
    print("📊 SEEDING SUMMARY")
    print("="*60)
    print(f"Total users: {total}")
    print(f"✅ Successfully created: {successful}")
    print(f"⚠️  Skipped (already exist): {skipped}")
    print(f"❌ Failed: {failed}")
    
    if failed_users:
        print(f"\n❌ Failed users:")
        for user_data, error in failed_users:
            print(f"   • {user_data['email']}: {error}")
    
    if successful_users:
        print_login_credentials(successful_users)
        print("\n🎉 Users created successfully! You can now test your application.")
        print("\n💡 TIP: All emails will be delivered to your main Gmail inbox")
        print("    because of the +tag format (Gmail feature)")
    
    if successful == total:
        print(f"\n✨ Perfect! All {total} users created successfully!")
    elif successful > 0:
        print(f"\n✅ {successful} out of {total} users created successfully.")

if __name__ == "__main__":
    main()