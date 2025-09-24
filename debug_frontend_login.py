#!/usr/bin/env python3
"""
Debug frontend login issues by testing with various credentials
"""

import requests
import json

def test_frontend_login():
    """Test login with various credentials that might be used in frontend"""
    print("🔍 Debugging Frontend Login Issues")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    login_url = f"{base_url}/api/v1/auth/login"
    
    # Test with various credentials that might exist
    test_credentials = [
        # Our known working test users
        {"email": "admin@test.com", "password": "Password123!", "desc": "Test Admin"},
        {"email": "member@test.com", "password": "Password123!", "desc": "Test Member"},
        {"email": "viewer@test.com", "password": "Password123!", "desc": "Test Viewer"},
        
        # Common credentials that might be in the database
        {"email": "admin@example.com", "password": "Password123!", "desc": "Example Admin"},
        {"email": "user@example.com", "password": "Password123!", "desc": "Example User"},
        {"email": "test@test.com", "password": "Password123!", "desc": "Test User"},
        
        # Try with different password variations
        {"email": "admin@test.com", "password": "password123", "desc": "Admin with lowercase"},
        {"email": "admin@test.com", "password": "Password123", "desc": "Admin without !"},
        {"email": "admin@test.com", "password": "NewPassword123!", "desc": "Admin with NewPassword"},
        
        # Try case variations
        {"email": "Admin@test.com", "password": "Password123!", "desc": "Admin with capital A"},
        {"email": "ADMIN@TEST.COM", "password": "Password123!", "desc": "Admin all caps"},
    ]
    
    successful_logins = []
    
    for creds in test_credentials:
        print(f"\n--- Testing {creds['desc']} ({creds['email']}) ---")
        
        try:
            # Make login request exactly like frontend
            response = requests.post(
                login_url,
                json={
                    "email": creds["email"],
                    "password": creds["password"]
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=10
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Login successful!")
                print(f"   User: {data.get('user', {}).get('first_name')} {data.get('user', {}).get('last_name')}")
                print(f"   Email: {data.get('user', {}).get('email')}")
                
                successful_logins.append({
                    "email": creds["email"],
                    "password": creds["password"],
                    "desc": creds["desc"]
                })
                
            elif response.status_code == 401:
                print(f"❌ 401 Unauthorized - Invalid credentials")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
            else:
                print(f"❌ Login failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                    
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection failed - is the server running?")
            break
        except Exception as e:
            print(f"❌ Request failed: {e}")
    
    print(f"\n" + "=" * 50)
    print(f"🎉 WORKING CREDENTIALS FOR FRONTEND:")
    print(f"=" * 50)
    
    if successful_logins:
        for login in successful_logins:
            print(f"✅ {login['desc']}")
            print(f"   Email: {login['email']}")
            print(f"   Password: {login['password']}")
            print()
    else:
        print("❌ No working credentials found!")
    
    print("Copy and paste these credentials into your frontend login form.")

if __name__ == "__main__":
    test_frontend_login()
