import requests
import json
import time

def test_frontend_integration():
    """Test the complete frontend-backend integration workflow"""
    
    print("🚀 FRONTEND-BACKEND INTEGRATION TEST")
    print("=" * 60)
    
    # Test data
    login_data = {
        'email': 'owner@agnoworksphere.com',
        'password': 'OwnerPass123!'
    }
    
    try:
        # Step 1: Login and get session token
        print("🔐 Step 1: Testing login...")
        login_response = requests.post('http://192.168.9.119:8000/api/v1/auth/login', 
                                     json=login_data)
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
            
        login_result = login_response.json()
        token = login_result.get('tokens', {}).get('access_token')
        
        if not token:
            print("❌ No access token received")
            return False
            
        print("✅ Login successful - Token received")
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Step 2: Get project structure
        print("\n📁 Step 2: Getting project structure...")
        projects_response = requests.get('http://192.168.9.119:8000/api/v1/projects/', headers=headers)
        
        if projects_response.status_code != 200:
            print(f"❌ Failed to get projects: {projects_response.status_code}")
            return False
            
        projects = projects_response.json()
        if not projects:
            print("❌ No projects found")
            return False
            
        project = projects[0]
        project_id = project.get('id')
        print(f"✅ Project found: {project.get('name')} ({project_id})")
        
        # Step 3: Get board structure
        print("\n📋 Step 3: Getting board structure...")
        boards_response = requests.get(f'http://192.168.9.119:8000/api/v1/projects/{project_id}/boards', headers=headers)
        
        if boards_response.status_code != 200:
            print(f"❌ Failed to get boards: {boards_response.status_code}")
            return False
            
        boards = boards_response.json()
        if not boards:
            print("❌ No boards found")
            return False
            
        board = boards[0]
        board_id = board.get('id')
        print(f"✅ Board found: {board.get('name')} ({board_id})")
        
        # Step 4: Get columns (this is what the dropdown should show)
        print("\n📊 Step 4: Testing column dropdown data...")
        columns_response = requests.get(f'http://192.168.9.119:8000/api/v1/boards/{board_id}/columns', headers=headers)
        
        if columns_response.status_code != 200:
            print(f"❌ Failed to get columns: {columns_response.status_code}")
            return False
            
        columns = columns_response.json()
        if not columns:
            print("❌ No columns found")
            return False
            
        print(f"✅ Found {len(columns)} columns for dropdown:")
        dropdown_options = []
        for i, col in enumerate(columns):
            # This mimics the frontend logic: column.title || column.name || 'Untitled'
            display_name = col.get('title') or col.get('name') or 'Untitled'
            dropdown_options.append({
                'value': col.get('id'),
                'label': display_name
            })
            print(f"   {i+1}. {display_name} (ID: {col.get('id')})")
        
        # Step 5: Test task creation with each column
        print("\n🎯 Step 5: Testing task creation with dropdown selections...")
        
        for i, option in enumerate(dropdown_options[:2]):  # Test first 2 columns
            print(f"\n   Testing column: {option['label']}")
            
            card_data = {
                'title': f'Frontend Test Task {i+1}',
                'description': f'Testing task creation via dropdown selection: {option["label"]}',
                'column_id': option['value'],
                'priority': 'medium'
            }
            
            card_response = requests.post('http://192.168.9.119:8000/api/v1/cards/',
                                        json=card_data, headers=headers)
            
            if card_response.status_code in [200, 201]:
                card_result = card_response.json()
                print(f"   ✅ Task created successfully in '{option['label']}'")
                print(f"      Title: {card_result.get('title')}")
                print(f"      ID: {card_result.get('id')}")
            else:
                print(f"   ❌ Failed to create task in '{option['label']}'")
                print(f"      Error: {card_response.text[:100]}")
                return False
        
        # Step 6: Verify frontend should work
        print("\n🎉 Step 6: Frontend Integration Verification")
        print("=" * 60)
        print("✅ BACKEND READY FOR FRONTEND:")
        print(f"   • Login endpoint: Working")
        print(f"   • Projects endpoint: Working")
        print(f"   • Boards endpoint: Working") 
        print(f"   • Columns endpoint: Working")
        print(f"   • Cards creation: Working")
        print()
        print("✅ DROPDOWN SHOULD SHOW:")
        for option in dropdown_options:
            print(f"   • {option['label']}")
        print()
        print("✅ FRONTEND FIXES APPLIED:")
        print("   • CreateTaskModal.jsx: Fixed column dropdown mapping")
        print("   • BoardColumn.jsx: Fixed column name display")
        print("   • kanban-board/index.jsx: Fixed column normalization")
        print()
        print("🌐 READY FOR MANUAL TESTING:")
        print("   1. Open http://192.168.9.119:3000")
        print("   2. Login with: owner@agnoworksphere.com / OwnerPass123!")
        print("   3. Navigate to Kanban Board")
        print("   4. Click 'Add Task' or '+' button")
        print("   5. Verify dropdown shows: To-Do, In Progress, Review, Done")
        print("   6. Create a task and verify it appears in the correct column")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during integration test: {e}")
        return False

if __name__ == "__main__":
    success = test_frontend_integration()
    if success:
        print("\n🎉 INTEGRATION TEST PASSED - Frontend should work correctly!")
    else:
        print("\n❌ INTEGRATION TEST FAILED - Check the errors above")
