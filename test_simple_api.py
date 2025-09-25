#!/usr/bin/env python3
"""
Simple test to check if API endpoints are accessible
"""
import asyncio
import aiohttp
import json

# Test configuration
API_BASE_URL = "http://192.168.9.119:8000"

async def test_simple_endpoints():
    """Test basic API endpoints without authentication"""
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test health endpoint
            print("🔍 Testing health endpoint...")
            async with session.get(f"{API_BASE_URL}/api/v1/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Health check passed: {data}")
                else:
                    print(f"❌ Health check failed: {resp.status}")
                    return
            
            # Test if we can reach the organizations endpoint (should return 401 without auth)
            print("\n🔍 Testing organizations endpoint (should return 401)...")
            async with session.get(f"{API_BASE_URL}/api/v1/organizations") as resp:
                print(f"📊 Organizations endpoint status: {resp.status}")
                if resp.status == 401:
                    print("✅ Organizations endpoint is accessible (returns 401 as expected)")
                else:
                    text = await resp.text()
                    print(f"Response: {text}")
            
            # Test CORS headers
            print("\n🔍 Testing CORS headers...")
            headers = {
                'Origin': 'http://192.168.9.119:3000',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'authorization'
            }
            async with session.options(f"{API_BASE_URL}/api/v1/organizations", headers=headers) as resp:
                print(f"📊 CORS preflight status: {resp.status}")
                cors_headers = {k: v for k, v in resp.headers.items() if 'access-control' in k.lower()}
                print(f"📊 CORS headers: {cors_headers}")
            
            print("\n✅ Basic API connectivity test completed!")
            
        except Exception as e:
            print(f"❌ Error during API testing: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Testing basic API connectivity...")
    asyncio.run(test_simple_endpoints())
