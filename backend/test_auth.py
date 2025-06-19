#!/usr/bin/env python3
"""
Test script for SchoolSecure Authentication System
This script tests the role-based authentication and authorization functionality.
"""

import requests
import json
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test user credentials (these should match your seeded users)
TEST_USERS = {
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

class AuthTester:
    def __init__(self):
        self.tokens = {}
        self.session = requests.Session()
    
    def test_login(self, role: str) -> bool:
        """Test login for a specific role"""
        print(f"\n🔐 Testing {role} login...")
        
        try:
            credentials = TEST_USERS[role]
            response = self.session.post(
                f"{API_BASE}/auth/login",
                json=credentials,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.tokens[role] = data["access_token"]
                user_info = data["user"]
                print(f"✅ {role} login successful")
                print(f"   User: {user_info['first_name']} {user_info['last_name']}")
                print(f"   Role: {user_info['role']}")
                print(f"   School: {user_info['school_name']}")
                return True
            else:
                print(f"❌ {role} login failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ {role} login error: {str(e)}")
            return False
    
    def test_protected_endpoint(self, role: str, endpoint: str, expected_status: int = 200) -> bool:
        """Test access to a protected endpoint"""
        if role not in self.tokens:
            print(f"❌ No token for {role}")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.tokens[role]}"}
            response = self.session.get(f"{API_BASE}{endpoint}", headers=headers)
            
            if response.status_code == expected_status:
                print(f"✅ {role} access to {endpoint}: {response.status_code}")
                return True
            else:
                print(f"❌ {role} access to {endpoint}: {response.status_code} (expected {expected_status})")
                if response.status_code == 403:
                    error_data = response.json()
                    print(f"   Forbidden: {error_data.get('detail', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ {role} access to {endpoint} error: {str(e)}")
            return False
    
    def test_role_authorization(self):
        """Test role-based authorization across all endpoints"""
        print(f"\n🛡️  Testing Role-Based Authorization...")
        
        # Test cases: (endpoint, student_access, teacher_access, admin_access)
        test_cases = [
            # Auth endpoints (all should have access)
            ("/auth/me", 200, 200, 200),
            ("/auth/check", 200, 200, 200),
            
            # Student-only endpoints
            ("/auth/student-only", 200, 403, 403),
            
            # Teacher endpoints (teachers and admins)
            ("/auth/teacher-only", 403, 200, 200),
            
            # Admin-only endpoints
            ("/auth/admin-only", 403, 403, 200),
            
            # Dashboard endpoints
            ("/dashboards/", 200, 200, 200),  # General dashboard
            ("/dashboards/teacher", 403, 200, 200),  # Teacher dashboard
            ("/dashboards/admin", 403, 403, 200),  # Admin dashboard
        ]
        
        success_count = 0
        total_tests = len(test_cases) * 3  # 3 roles per test case
        
        for endpoint, student_expected, teacher_expected, admin_expected in test_cases:
            print(f"\n  Testing {endpoint}:")
            
            # Test student access
            if self.test_protected_endpoint("student", endpoint, student_expected):
                success_count += 1
            
            # Test teacher access  
            if self.test_protected_endpoint("teacher", endpoint, teacher_expected):
                success_count += 1
                
            # Test admin access
            if self.test_protected_endpoint("admin", endpoint, admin_expected):
                success_count += 1
        
        print(f"\n📊 Authorization Tests: {success_count}/{total_tests} passed")
        return success_count == total_tests
    
    def test_token_refresh(self, role: str) -> bool:
        """Test token refresh functionality"""
        print(f"\n🔄 Testing {role} token refresh...")
        
        if role not in self.tokens:
            print(f"❌ No token for {role}")
            return False
        
        try:
            # First, get the refresh token from login
            credentials = TEST_USERS[role]
            response = self.session.post(
                f"{API_BASE}/auth/login",
                json=credentials
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to get refresh token for {role}")
                return False
            
            refresh_token = response.json()["refresh_token"]
            
            # Now test refresh
            refresh_response = self.session.post(
                f"{API_BASE}/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            if refresh_response.status_code == 200:
                print(f"✅ {role} token refresh successful")
                new_data = refresh_response.json()
                self.tokens[role] = new_data["access_token"]  # Update token
                return True
            else:
                print(f"❌ {role} token refresh failed: {refresh_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ {role} token refresh error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all authentication tests"""
        print("🧪 SchoolSecure Authentication System Test Suite")
        print("=" * 60)
        
        # Test 1: Login for all roles
        login_results = []
        for role in ["student", "teacher", "admin"]:
            login_results.append(self.test_login(role))
        
        if not all(login_results):
            print("\n❌ Login tests failed. Cannot proceed with other tests.")
            return False
        
        # Test 2: Role-based authorization
        auth_success = self.test_role_authorization()
        
        # Test 3: Token refresh
        refresh_results = []
        for role in ["student", "teacher", "admin"]:
            refresh_results.append(self.test_token_refresh(role))
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY:")
        print(f"   ✅ Login Tests: {'PASSED' if all(login_results) else 'FAILED'}")
        print(f"   ✅ Authorization Tests: {'PASSED' if auth_success else 'FAILED'}")
        print(f"   ✅ Token Refresh Tests: {'PASSED' if all(refresh_results) else 'FAILED'}")
        
        overall_success = all(login_results) and auth_success and all(refresh_results)
        print(f"\n🎯 OVERALL RESULT: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        return overall_success

def main():
    """Main test runner"""
    tester = AuthTester()
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not responding correctly")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on http://127.0.0.1:8000")
        print("   Start server with: uvicorn backend.main:app --reload")
        sys.exit(1)
    
    # Run tests
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All authentication tests passed! The system is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()