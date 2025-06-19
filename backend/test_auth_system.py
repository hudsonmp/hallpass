#!/usr/bin/env python3
"""
Authentication System Test Script for SchoolSecure Backend

This script tests the comprehensive role-based authentication system including:
- Login with email/password
- JWT token validation 
- Refresh token functionality
- Role-based endpoint access control
- Supabase RLS policy enforcement

Usage:
    python test_auth_system.py

Make sure your backend server is running on http://127.0.0.1:8000
"""

import requests
import json
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1"

# Test user credentials (from seed data)
TEST_USERS = {
    "admin": {
        "email": "hudsonmitchellpullman+admin@gmail.com",
        "password": "2010Testing!",
        "expected_role": "administrator"
    },
    "teacher1": {
        "email": "hudsonmitchellpullman+teacher1@gmail.com", 
        "password": "2010Testing!",
        "expected_role": "teacher"
    },
    "teacher2": {
        "email": "hudsonmitchellpullman+teacher2@gmail.com",
        "password": "2010Testing!", 
        "expected_role": "teacher"
    },
    "student1": {
        "email": "hudsonmitchellpullman+student1@gmail.com",
        "password": "2010Testing!",
        "expected_role": "student"
    },
    "student2": {
        "email": "hudsonmitchellpullman+student2@gmail.com",
        "password": "2010Testing!",
        "expected_role": "student"
    }
}

class AuthTestClient:
    def __init__(self, base_url: str):
        """
        Initialize an AuthTestClient instance for managing authentication requests and tokens.
        
        Parameters:
            base_url (str): The base URL of the backend API.
        """
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_info: Optional[Dict[str, Any]] = None
        
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user by sending credentials to the login endpoint.
        
        Parameters:
            email (str): The user's email address.
            password (str): The user's password.
        
        Returns:
            Dict[str, Any]: The response data containing access token, refresh token, and user information.
        
        Raises:
            Exception: If authentication fails or the server returns a non-200 status code.
        """
        url = f"{self.base_url}/auth/login"
        data = {"email": email, "password": password}
        
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            self.access_token = result["access_token"]
            self.refresh_token = result["refresh_token"]
            self.user_info = result["user"]
            return result
        else:
            raise Exception(f"Login failed: {response.status_code} - {response.text}")
    
    def refresh_session(self) -> Dict[str, Any]:
        """
        Refreshes the authentication session using the current refresh token.
        
        Returns:
            dict: The response containing new access and refresh tokens, and user information.
        
        Raises:
            Exception: If no refresh token is available or the refresh request fails.
        """
        if not self.refresh_token:
            raise Exception("No refresh token available")
            
        url = f"{self.base_url}/auth/refresh"
        data = {"refresh_token": self.refresh_token}
        
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            self.access_token = result["access_token"]
            self.refresh_token = result["refresh_token"]
            self.user_info = result["user"]
            return result
        else:
            raise Exception(f"Refresh failed: {response.status_code} - {response.text}")
    
    def get_headers(self) -> Dict[str, str]:
        """
        Return HTTP headers containing the Bearer access token for authenticated requests.
        
        Raises:
            Exception: If no access token is available.
        Returns:
            A dictionary with the Authorization header set to the current access token.
        """
        if not self.access_token:
            raise Exception("No access token available")
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def test_endpoint(self, method: str, endpoint: str, expected_status: int = 200, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Sends an authenticated HTTP request to a specified endpoint and verifies the response status.
        
        Parameters:
            method (str): The HTTP method to use ("GET", "POST", or "PATCH").
            endpoint (str): The API endpoint path to test.
            expected_status (int, optional): The expected HTTP status code. Defaults to 200.
            data (dict, optional): JSON data to include in the request body for POST or PATCH methods.
        
        Returns:
            dict: A dictionary containing the actual status code, expected status, success flag, and response data.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers()
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data or {})
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data or {})
        else:
            raise Exception(f"Unsupported method: {method}")
        
        result = {
            "status_code": response.status_code,
            "expected": expected_status,
            "success": response.status_code == expected_status
        }
        
        try:
            result["data"] = response.json()
        except:
            result["data"] = response.text
            
        return result

def test_authentication_flow():
    """
    Tests the basic authentication flow, including login, token validation, and token refresh for an administrator user.
    
    This function logs in with administrator credentials, verifies the returned role and tokens, validates the access token via a protected endpoint, and tests the refresh token functionality. Results and errors are printed to the console.
    """
    print("🔐 Testing Authentication Flow")
    print("=" * 50)
    
    client = AuthTestClient(BASE_URL)
    
    # Test login with admin user
    admin_creds = TEST_USERS["admin"]
    print(f"📝 Testing login with admin: {admin_creds['email']}")
    
    try:
        login_result = client.login(admin_creds["email"], admin_creds["password"])
        print(f"✅ Login successful!")
        print(f"   - Role: {login_result['user']['role']}")
        print(f"   - Token type: {login_result['token_type']}")
        print(f"   - Has access token: {bool(login_result['access_token'])}")
        print(f"   - Has refresh token: {bool(login_result['refresh_token'])}")
        
        # Test token validation
        print(f"\n🔍 Testing token validation...")
        me_result = client.test_endpoint("GET", "/auth/me")
        if me_result["success"]:
            print(f"✅ Token validation successful!")
            print(f"   - User ID: {me_result['data']['id']}")
            print(f"   - Email: {me_result['data']['email']}")
            print(f"   - Role: {me_result['data']['role']}")
        else:
            print(f"❌ Token validation failed: {me_result}")
        
        # Test refresh token
        print(f"\n🔄 Testing refresh token...")
        refresh_result = client.refresh_session()
        print(f"✅ Refresh successful!")
        print(f"   - New token received: {bool(refresh_result['access_token'])}")
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")

def test_role_based_access():
    """
    Test access permissions for administrator, teacher, and student roles across protected endpoints.
    
    For each test user, logs in and verifies that access to role-specific and restricted endpoints returns the expected HTTP status codes, confirming correct enforcement of role-based access control.
    """
    print("\n🛡️ Testing Role-Based Access Control")
    print("=" * 50)
    
    # Test each user role
    for user_type, creds in TEST_USERS.items():
        print(f"\n👤 Testing {user_type}: {creds['email']}")
        
        client = AuthTestClient(BASE_URL)
        
        try:
            # Login
            login_result = client.login(creds["email"], creds["password"])
            role = login_result["user"]["role"]
            print(f"   ✅ Logged in as {role}")
            
            # Test endpoints based on role
            if role == "administrator":
                print("   🧪 Testing admin endpoints...")
                
                # Admin dashboard (should work)
                result = client.test_endpoint("GET", "/dashboard/admin", 200)
                status = "✅" if result["success"] else "❌"
                print(f"   {status} Admin dashboard: {result['status_code']}")
                
                # School settings (should work)
                result = client.test_endpoint("GET", "/schools/me", 200)
                status = "✅" if result["success"] else "❌"
                print(f"   {status} School settings: {result['status_code']}")
                
            elif role == "teacher":
                print("   🧪 Testing teacher endpoints...")
                
                # Teacher dashboard (should work)
                result = client.test_endpoint("GET", "/dashboard/teacher", 200)
                status = "✅" if result["success"] else "❌"
                print(f"   {status} Teacher dashboard: {result['status_code']}")
                
                # Admin dashboard (should fail)
                result = client.test_endpoint("GET", "/dashboard/admin", 403)
                status = "✅" if result["success"] else "❌"
                print(f"   {status} Admin dashboard (forbidden): {result['status_code']}")
                
                # View passes (should work)
                result = client.test_endpoint("GET", "/passes/", 200)
                status = "✅" if result["success"] else "❌"
                print(f"   {status} View passes: {result['status_code']}")
                
            elif role == "student":
                print("   🧪 Testing student endpoints...")
                
                # Student dashboard (should work) 
                result = client.test_endpoint("GET", "/dashboard/student", 200)
                status = "✅" if result["success"] else "❌"
                print(f"   {status} Student dashboard: {result['status_code']}")
                
                # Admin dashboard (should fail)
                result = client.test_endpoint("GET", "/dashboard/admin", 403)
                status = "✅" if result["success"] else "❌"
                print(f"   {status} Admin dashboard (forbidden): {result['status_code']}")
                
                # Teacher dashboard (should fail)
                result = client.test_endpoint("GET", "/dashboard/teacher", 403)
                status = "✅" if result["success"] else "❌"
                print(f"   {status} Teacher dashboard (forbidden): {result['status_code']}")
                
                # View own passes (should work)
                result = client.test_endpoint("GET", "/passes/", 200)
                status = "✅" if result["success"] else "❌"
                print(f"   {status} View own passes: {result['status_code']}")
                
        except Exception as e:
            print(f"   ❌ Test failed for {user_type}: {e}")

def test_invalid_credentials():
    """
    Test login attempts with invalid credentials and malformed requests, ensuring the backend correctly rejects unauthorized or improperly formatted authentication attempts.
    """
    print("\n🚫 Testing Invalid Credentials")
    print("=" * 50)
    
    client = AuthTestClient(BASE_URL)
    
    # Test invalid email
    print("📝 Testing invalid email...")
    try:
        client.login("invalid@email.com", "password")
        print("❌ Should have failed!")
    except Exception as e:
        print(f"✅ Correctly rejected invalid email: {e}")
    
    # Test invalid password
    print("\n📝 Testing invalid password...")
    try:
        client.login(TEST_USERS["admin"]["email"], "wrongpassword")
        print("❌ Should have failed!")
    except Exception as e:
        print(f"✅ Correctly rejected invalid password: {e}")
    
    # Test malformed requests
    print("\n📝 Testing malformed requests...")
    url = f"{BASE_URL}/auth/login"
    
    # Missing email
    response = requests.post(url, json={"password": "test"})
    status = "✅" if response.status_code == 422 else "❌"
    print(f"{status} Missing email: {response.status_code}")
    
    # Missing password  
    response = requests.post(url, json={"email": "test@test.com"})
    status = "✅" if response.status_code == 422 else "❌"
    print(f"{status} Missing password: {response.status_code}")

def test_token_expiration():
    """
    Tests token expiration handling and refresh logic, including multiple refresh attempts and rejection of invalid refresh tokens.
    
    This function logs in as the admin user, verifies token validity, performs several refresh operations to ensure tokens are updated correctly, and checks that an invalid refresh token is properly rejected by the backend.
    """
    print("\n⏰ Testing Token Management")
    print("=" * 50)
    
    client = AuthTestClient(BASE_URL)
    
    # Login
    admin_creds = TEST_USERS["admin"]
    client.login(admin_creds["email"], admin_creds["password"])
    print("✅ Logged in")
    
    # Test valid token
    result = client.test_endpoint("GET", "/auth/check", 200)
    status = "✅" if result["success"] else "❌"
    print(f"{status} Valid token check: {result['status_code']}")
    
    # Test refresh token multiple times
    print("\n🔄 Testing multiple refresh attempts...")
    for i in range(3):
        try:
            client.refresh_session()
            print(f"✅ Refresh {i+1}: Success")
        except Exception as e:
            print(f"❌ Refresh {i+1}: {e}")
    
    # Test with invalid refresh token
    print("\n🔄 Testing invalid refresh token...")
    client.refresh_token = "invalid_token"
    try:
        client.refresh_session()
        print("❌ Should have failed!")
    except Exception as e:
        print(f"✅ Correctly rejected invalid refresh token: {e}")

def main():
    """
    Executes the full authentication test suite for the SchoolSecure backend, including login, role-based access, invalid credential handling, and token management tests.
    
    Prints detailed results for each test and handles connection errors or unexpected exceptions gracefully.
    """
    print("🚀 SchoolSecure Authentication System Test Suite")
    print("=" * 60)
    
    try:
        # Test basic authentication
        test_authentication_flow()
        
        # Test role-based access control
        test_role_based_access()
        
        # Test invalid credentials
        test_invalid_credentials()
        
        # Test token management
        test_token_expiration()
        
        print("\n🎉 All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the backend server.")
        print("Make sure the FastAPI server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"❌ Test suite failed: {e}")

if __name__ == "__main__":
    main()