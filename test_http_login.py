#!/usr/bin/env python3
"""
Test the HTTP login endpoint
"""

import requests
import json

def test_http_login():
    """Test the HTTP login endpoint"""
    print("🌐 Testing HTTP Login Endpoint")
    print("=" * 35)
    
    base_url = "http://localhost:8000"
    login_url = f"{base_url}/api/v1/auth/login"
    
    test_credentials = [
        {"email": "admin@test.com", "password": "Password123!", "role": "admin"},
        {"email": "member@test.com", "password": "Password123!", "role": "member"},
        {"email": "viewer@test.com", "password": "Password123!", "role": "viewer"},
    ]
    
    for creds in test_credentials:
        print(f"\n--- Testing {creds['email']} ---")
        
        try:
            # Make login request
            response = requests.post(
                login_url,
                json={
                    "email": creds["email"],
                    "password": creds["password"]
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Login successful!")
                print(f"   User: {data.get('user', {}).get('first_name')} {data.get('user', {}).get('last_name')}")
                print(f"   Email: {data.get('user', {}).get('email')}")
                print(f"   Token: {data.get('access_token', '')[:20]}...")
                
                if 'organization' in data and data['organization']:
                    print(f"   Organization: {data['organization'].get('name')}")
                    print(f"   Role: {data['organization'].get('role')}")
                
            else:
                print(f"❌ Login failed!")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                    
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection failed - is the server running on {base_url}?")
        except requests.exceptions.Timeout:
            print(f"❌ Request timeout")
        except Exception as e:
            print(f"❌ Request failed: {e}")
    
    print(f"\n🎉 HTTP login testing complete!")

if __name__ == "__main__":
    test_http_login()
