import requests
import json

def test_modal_debugging():
    """Debug the modal column loading issue"""
    
    print("🔍 MODAL DEBUGGING TEST")
    print("=" * 50)
    
    login_data = {
        'email': 'owner@agnoworksphere.com',
        'password': 'OwnerPass123!'
    }
    
    try:
        # Login
        print("🔐 Logging in...")
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
            
        print("✅ Login successful")
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Test all the API endpoints that CreateTaskModal uses
        print("\n📋 Testing API endpoints used by CreateTaskModal...")
        
        # 1. Get projects
        print("\n1. Testing projects endpoint...")
        projects_response = requests.get('http://192.168.9.119:8000/api/v1/projects/', headers=headers)
        print(f"   Status: {projects_response.status_code}")
        
        if projects_response.status_code == 200:
            projects = projects_response.json()
            print(f"   Projects found: {len(projects)}")
            if projects:
                project = projects[0]
                project_id = project.get('id')
                print(f"   First project: {project.get('name')} (ID: {project_id})")
                
                # 2. Get boards for project
                print(f"\n2. Testing boards endpoint for project {project_id}...")
                boards_response = requests.get(f'http://192.168.9.119:8000/api/v1/projects/{project_id}/boards', headers=headers)
                print(f"   Status: {boards_response.status_code}")
                
                if boards_response.status_code == 200:
                    boards = boards_response.json()
                    print(f"   Boards found: {len(boards)}")
                    if boards:
                        board = boards[0]
                        board_id = board.get('id')
                        print(f"   First board: {board.get('name')} (ID: {board_id})")
                        
                        # 3. Get columns for board
                        print(f"\n3. Testing columns endpoint for board {board_id}...")
                        columns_response = requests.get(f'http://192.168.9.119:8000/api/v1/boards/{board_id}/columns', headers=headers)
                        print(f"   Status: {columns_response.status_code}")
                        
                        if columns_response.status_code == 200:
                            columns = columns_response.json()
                            print(f"   Columns found: {len(columns)}")
                            
                            print("\n📊 COLUMN DATA FOR DROPDOWN:")
                            print("   " + "="*40)
                            for i, col in enumerate(columns):
                                title = col.get('title')
                                name = col.get('name')
                                display_name = title or name or 'Untitled'
                                print(f"   {i+1}. Display: '{display_name}'")
                                print(f"      ID: {col.get('id')}")
                                print(f"      Title: {title}")
                                print(f"      Name: {name}")
                                print(f"      Position: {col.get('position')}")
                                print()
                            
                            # 4. Test team members endpoint
                            print("4. Testing team members endpoint...")
                            members_response = requests.get(f'http://192.168.9.119:8000/api/v1/projects/{project_id}/members', headers=headers)
                            print(f"   Status: {members_response.status_code}")
                            
                            if members_response.status_code == 200:
                                members = members_response.json()
                                print(f"   Members found: {len(members)}")
                            else:
                                print(f"   Members error: {members_response.text[:100]}")
                            
                            print("\n🎯 FRONTEND DEBUGGING INSTRUCTIONS:")
                            print("="*50)
                            print("1. Open browser console (F12)")
                            print("2. Navigate to the page with 'Create New Task' modal")
                            print("3. Open the modal")
                            print("4. Look for these console messages:")
                            print("   - '📋 Boards loaded: [...]'")
                            print("   - '📊 Columns loaded: [...]'")
                            print("   - '🔍 CreateTaskModal Debug: {...}'")
                            print("5. If columns array is empty, check:")
                            print("   - Is projectId being passed correctly?")
                            print("   - Are there any API errors?")
                            print("   - Is the user authenticated?")
                            
                            print(f"\n✅ EXPECTED DROPDOWN OPTIONS:")
                            for col in columns:
                                display_name = col.get('title') or col.get('name') or 'Untitled'
                                print(f"   • {display_name}")
                            
                            return True
                        else:
                            print(f"   Columns error: {columns_response.text[:100]}")
                    else:
                        print("   No boards found")
                else:
                    print(f"   Boards error: {boards_response.text[:100]}")
            else:
                print("   No projects found")
        else:
            print(f"   Projects error: {projects_response.text[:100]}")
            
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_modal_debugging()
