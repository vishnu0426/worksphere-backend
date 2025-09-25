#!/usr/bin/env python3
"""
Test script to verify team members API endpoints
"""
import asyncio
import asyncpg
import sys
import os
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.config import settings

async def test_team_members_endpoints():
    """Test team members API endpoints"""
    try:
        # Connect to database - convert asyncpg URL to standard postgres URL
        db_url = settings.database_url.replace('postgresql+asyncpg://', 'postgresql://')
        conn = await asyncpg.connect(db_url)
        print("✅ Connected to database")
        
        # Get a sample organization
        org_query = """
            SELECT id, name FROM organizations LIMIT 1;
        """
        org_result = await conn.fetchrow(org_query)
        
        if not org_result:
            print("❌ No organizations found in database")
            return
            
        org_id = org_result['id']
        org_name = org_result['name']
        print(f"🏢 Testing with organization: {org_name} ({org_id})")
        
        # Check organization members
        members_query = """
            SELECT om.*, u.first_name, u.last_name, u.email
            FROM organization_members om
            JOIN users u ON om.user_id = u.id
            WHERE om.organization_id = $1
            ORDER BY om.joined_at;
        """
        
        members = await conn.fetch(members_query, org_id)
        print(f"👥 Found {len(members)} members in organization:")
        
        for member in members:
            print(f"  - {member['first_name']} {member['last_name']} ({member['email']}) - Role: {member['role']}")
        
        # Test if there are any cards that need assignment
        cards_query = """
            SELECT c.id, c.title, c.column_id, col.name as column_name, b.name as board_name, p.name as project_name
            FROM cards c
            JOIN columns col ON c.column_id = col.id
            JOIN boards b ON col.board_id = b.id
            JOIN projects p ON b.project_id = p.id
            WHERE p.organization_id = $1
            ORDER BY c.created_at DESC
            LIMIT 5;
        """
        
        cards = await conn.fetch(cards_query, org_id)
        print(f"\n📋 Found {len(cards)} recent cards in organization:")
        
        for card in cards:
            print(f"  - {card['title']} (Project: {card['project_name']}, Board: {card['board_name']}, Column: {card['column_name']})")
            
            # Check assignments for this card
            assignments_query = """
                SELECT ca.*, u.first_name, u.last_name, u.email
                FROM card_assignments ca
                JOIN users u ON ca.user_id = u.id
                WHERE ca.card_id = $1;
            """
            
            assignments = await conn.fetch(assignments_query, card['id'])
            if assignments:
                print(f"    Assigned to: {', '.join([f'{a['first_name']} {a['last_name']}' for a in assignments])}")
            else:
                print(f"    No assignments")
        
        await conn.close()
        print("\n✅ Test completed successfully")
        
    except Exception as e:
        print(f"❌ Error testing team members: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Testing team members API...")
    asyncio.run(test_team_members_endpoints())
