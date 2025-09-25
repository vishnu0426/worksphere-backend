#!/usr/bin/env python3
"""
Test script to verify API endpoints are working correctly
"""
import asyncio
import aiohttp
import json
import sys
import os

# Test configuration
API_BASE_URL = "http://192.168.9.119:8000"
TEST_EMAIL = "vishnu@zoho.com"  # From our database test
TEST_PASSWORD = "password123"  # You'll need to set this

async def test_api_endpoints():
    """Test API endpoints for team members and kanban functionality"""
    
    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Login to get authentication token
            print("🔐 Testing authentication...")
            login_data = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
            
            async with session.post(
                f"{API_BASE_URL}/api/v1/auth/login",
                json=login_data
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Login failed: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return
                
                auth_data = await resp.json()
                token = auth_data.get("access_token")
                if not token:
                    print("❌ No access token received")
                    return
                
                print("✅ Authentication successful")
            
            # Set authorization header for subsequent requests
            headers = {"Authorization": f"Bearer {token}"}
            
            # Step 2: Get user's organizations
            print("\n🏢 Testing organizations...")
            async with session.get(
                f"{API_BASE_URL}/api/v1/users/me/organizations",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Failed to get organizations: {resp.status}")
                    return
                
                orgs_data = await resp.json()
                if not orgs_data:
                    print("❌ No organizations found")
                    return
                
                org_id = orgs_data[0]["id"]
                org_name = orgs_data[0]["name"]
                print(f"✅ Found organization: {org_name} ({org_id})")
            
            # Step 3: Test team members endpoint
            print(f"\n👥 Testing team members for organization {org_id}...")
            async with session.get(
                f"{API_BASE_URL}/api/v1/organizations/{org_id}/members",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Failed to get team members: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return
                
                members_data = await resp.json()
                print(f"✅ Found {len(members_data)} team members:")
                for member in members_data[:3]:  # Show first 3
                    user = member.get("user", {})
                    print(f"  - {user.get('first_name', '')} {user.get('last_name', '')} ({user.get('email', '')}) - Role: {member.get('role', '')}")
            
            # Step 4: Get projects for the organization
            print(f"\n📁 Testing projects for organization {org_id}...")
            async with session.get(
                f"{API_BASE_URL}/api/v1/projects?organization_id={org_id}",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Failed to get projects: {resp.status}")
                    return
                
                projects_data = await resp.json()
                if not projects_data:
                    print("❌ No projects found")
                    return
                
                project_id = projects_data[0]["id"]
                project_name = projects_data[0]["name"]
                print(f"✅ Found project: {project_name} ({project_id})")
            
            # Step 5: Test kanban board endpoint
            print(f"\n📋 Testing kanban board for project {project_id}...")
            async with session.get(
                f"{API_BASE_URL}/api/v1/kanban/projects/{project_id}/board",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Failed to get kanban board: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return
                
                board_data = await resp.json()
                print(f"✅ Found kanban board: {board_data.get('name', 'Unnamed')}")
                print(f"   Columns: {len(board_data.get('columns', []))}")
                
                # Count total cards
                total_cards = 0
                for column in board_data.get('columns', []):
                    cards = column.get('cards', [])
                    total_cards += len(cards)
                    if cards:
                        print(f"   Column '{column.get('name', '')}': {len(cards)} cards")
                        for card in cards[:2]:  # Show first 2 cards
                            assignments = card.get('assignments', [])
                            print(f"     - {card.get('title', '')} (Assignments: {len(assignments)})")
                
                print(f"   Total cards: {total_cards}")
            
            print("\n✅ All API endpoint tests completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during API testing: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Testing API endpoints...")
    asyncio.run(test_api_endpoints())
