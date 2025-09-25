#!/usr/bin/env python3
"""
Test script to verify the assignable members API endpoint
"""
import asyncio
import asyncpg
import sys

# Database URL
DATABASE_URL = "postgresql://postgres:Admin@192.168.9.119:5432/agno_worksphere"

async def test_assignable_members():
    """Test the assignable members functionality"""
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to database")
        
        # Get a sample card ID
        card_result = await conn.fetchrow("SELECT id, title FROM cards LIMIT 1;")
        if not card_result:
            print("❌ No cards found in database")
            await conn.close()
            return
            
        card_id = card_result['id']
        card_title = card_result['title']
        print(f"📋 Testing with card: {card_title} (ID: {card_id})")
        
        # Get organization members for this card
        query = """
            SELECT DISTINCT 
                u.id,
                u.first_name,
                u.last_name,
                u.email,
                om.role
            FROM cards c
            JOIN columns col ON c.column_id = col.id
            JOIN boards b ON col.board_id = b.id
            JOIN projects p ON b.project_id = p.id
            JOIN organization_members om ON om.organization_id = p.organization_id
            JOIN users u ON om.user_id = u.id
            WHERE c.id = $1
            ORDER BY u.first_name;
        """
        
        members = await conn.fetch(query, card_id)
        print(f"👥 Found {len(members)} organization members:")
        
        for member in members:
            print(f"  - {member['first_name']} {member['last_name']} ({member['email']}) - {member['role']}")
        
        # Test card assignments
        assignments_query = """
            SELECT ca.*, u.first_name, u.last_name, u.email
            FROM card_assignments ca
            JOIN users u ON ca.user_id = u.id
            WHERE ca.card_id = $1;
        """
        
        assignments = await conn.fetch(assignments_query, card_id)
        print(f"🎯 Current assignments for this card: {len(assignments)}")
        
        for assignment in assignments:
            print(f"  - {assignment['first_name']} {assignment['last_name']} ({assignment['email']})")
        
        await conn.close()
        print("✅ Test completed successfully")
        
    except Exception as e:
        print(f"❌ Error testing assignable members: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Testing assignable members API...")
    asyncio.run(test_assignable_members())
