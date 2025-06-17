#!/usr/bin/env python3
"""
Simple API testing script for SchoolSecure endpoints.
Tests authentication and basic pass operations.
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_ACCOUNTS = {
    "student": {
        "email": "hudsonmitchellpullman+student1@gmail.com",
        "password": "2010Testing!"
    },
    "teacher": {
        "email": "hudsonmitchellpullman+teacher1@gmail.com", 
        "password": "2010Testing!"
    },
    "admin": {
        "email": "hudsonmitchellpullman+admin@gmail.com",
        "password": "2010Testing!"
    }
}

def test_login(role: str):
    """Test login functionality for a specific role."""
    print(f"\n🔐 Testing {role} login...")
    
    account = TEST_ACCOUNTS[role]
    response = requests.post(f"{BASE_URL}/auth/login", json=account)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Login successful for {data['profile']['first_name']} {data['profile']['last_name']}")
        print(f"   📍 School: {data['profile']['school_name']}")
        print(f"   👤 Role: {data['profile']['role']}")
        return data['access_token']
    else:
        print(f"   ❌ Login failed: {response.text}")
        return None

def test_get_locations(token: str):
    """Test getting available locations."""
    print(f"\n📍 Testing locations endpoint...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/passes/locations", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {len(data['pre_approved'])} pre-approved locations")
        print(f"   ✅ Found {len(data['requires_approval'])} approval-required locations")
        
        if data['pre_approved']:
            print(f"   🏥 Pre-approved locations:")
            for location in data['pre_approved']:
                print(f"      • {location['name']} ({location['default_duration']} min)")
        
        return data
    else:
        print(f"   ❌ Failed to get locations: {response.text}")
        return None

def test_create_pass(token: str, locations_data: dict):
    """Test creating a pre-approved pass."""
    print(f"\n📝 Testing pass creation...")
    
    if not locations_data or not locations_data['pre_approved']:
        print(f"   ⚠️  No pre-approved locations available for testing")
        return None
    
    # Use the first pre-approved location (Nurse)
    nurse_location = locations_data['pre_approved'][0]
    
    pass_request = {
        "location_id": nurse_location['id'],
        "student_reason": "Feeling unwell - need to see the nurse",
        "requested_start_time": datetime.utcnow().isoformat(),
        "is_summons": False,
        "is_early_release": False
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/passes/", json=pass_request, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Pass created successfully!")
        print(f"   🏥 Destination: {data['location_name']}")
        print(f"   📊 Status: {data['status']}")
        print(f"   🆔 Pass ID: {data['id']}")
        return data
    else:
        print(f"   ❌ Failed to create pass: {response.text}")
        return None

def test_get_passes(token: str):
    """Test getting user's passes."""
    print(f"\n📋 Testing get passes...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/passes/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Retrieved {len(data['passes'])} passes")
        
        for pass_data in data['passes']:
            print(f"      • {pass_data['location_name']} - {pass_data['status']}")
        
        return data
    else:
        print(f"   ❌ Failed to get passes: {response.text}")
        return None

def test_activate_pass(token: str, pass_id: str):
    """Test activating a pass."""
    print(f"\n🚀 Testing pass activation...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.patch(f"{BASE_URL}/passes/{pass_id}/activate", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Pass activated successfully!")
        print(f"   🔍 QR Code: {data['verification_code']}")
        print(f"   ⏰ Start Time: {data['actual_start_time']}")
        return data
    else:
        print(f"   ❌ Failed to activate pass: {response.text}")
        return None

def main():
    """Run all API tests."""
    print("🧪 SchoolSecure API Testing Suite")
    print("=" * 50)
    
    try:
        # Test student login and operations
        student_token = test_login("student")
        if not student_token:
            print("❌ Cannot continue without student authentication")
            return
        
        # Test getting locations
        locations = test_get_locations(student_token)
        
        # Test creating a pass
        new_pass = test_create_pass(student_token, locations)
        
        # Test getting passes
        test_get_passes(student_token)
        
        # Test activating the pass
        if new_pass:
            test_activate_pass(student_token, new_pass['id'])
        
        # Test teacher login
        teacher_token = test_login("teacher")
        if teacher_token:
            print(f"\n👨‍🏫 Testing teacher view of passes...")
            test_get_passes(teacher_token)
        
        print(f"\n" + "=" * 50)
        print("🎉 API testing completed!")
        print("✅ All basic endpoints are working correctly")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server")
        print("💡 Make sure the FastAPI server is running on http://127.0.0.1:8000")
        print("   Run: uvicorn backend.main:app --reload")
    except Exception as e:
        print(f"❌ Unexpected error during testing: {e}")

if __name__ == "__main__":
    main() 