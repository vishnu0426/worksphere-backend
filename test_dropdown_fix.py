import requests
import json

# Test the complete task creation workflow
login_data = {
    'email': 'owner@agnoworksphere.com',
    'password': 'OwnerPass123!'
}

try:
    # Login
    print('🔐 Testing login...')
    login_response = requests.post('http://localhost:8000/api/v1/auth/login', 
                                 json=login_data)
    
    if login_response.status_code == 200:
        login_result = login_response.json()
        token = login_result.get('tokens', {}).get('access_token')
        
        if token:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Get project and board info
            projects_response = requests.get('http://localhost:8000/api/v1/projects/', headers=headers)
            if projects_response.status_code == 200:
                projects = projects_response.json()
                if projects:
                    project = projects[0]
                    project_id = project.get('id')
                    
                    # Get boards
                    boards_response = requests.get(f'http://localhost:8000/api/v1/projects/{project_id}/boards', headers=headers)
                    if boards_response.status_code == 200:
                        boards = boards_response.json()
                        if boards:
                            board = boards[0]
                            board_id = board.get('id')
                            
                            # Get columns with detailed info
                            columns_response = requests.get(f'http://localhost:8000/api/v1/boards/{board_id}/columns', headers=headers)
                            if columns_response.status_code == 200:
                                columns = columns_response.json()
                                
                                print('🎯 COLUMN DROPDOWN TEST RESULTS:')
                                print('=' * 50)
                                for i, col in enumerate(columns):
                                    print(f'Column {i+1}:')
                                    print(f'  ID: {col.get("id")}')
                                    print(f'  Name: "{col.get("name")}"')
                                    print(f'  Title: {col.get("title")}')
                                    print(f'  Display (title || name): "{col.get("title") or col.get("name") or "Untitled"}"')
                                    print()
                                
                                # Test card creation with each column
                                print('🚀 TESTING CARD CREATION:')
                                print('=' * 50)
                                
                                for i, col in enumerate(columns[:2]):  # Test first 2 columns
                                    card_data = {
                                        'title': f'Test Task {i+1}',
                                        'description': f'Testing dropdown fix for column: {col.get("name")}',
                                        'column_id': col.get('id'),
                                        'priority': 'medium'
                                    }
                                    
                                    card_response = requests.post('http://localhost:8000/api/v1/cards/',
                                                                json=card_data, headers=headers)
                                    
                                    if card_response.status_code in [200, 201]:
                                        card_result = card_response.json()
                                        print(f'✅ Card created in "{col.get("name")}" column')
                                        print(f'   Title: {card_result.get("title")}')
                                        print(f'   ID: {card_result.get("id")}')
                                    else:
                                        print(f'❌ Failed to create card in "{col.get("name")}" column')
                                        print(f'   Error: {card_response.text[:100]}')
                                    print()
                                
                                print('🎉 FRONTEND DROPDOWN SHOULD NOW SHOW:')
                                print('=' * 50)
                                for col in columns:
                                    display_name = col.get('title') or col.get('name') or 'Untitled'
                                    print(f'• {display_name}')
                                
                            else:
                                print('❌ Failed to get columns')
                        else:
                            print('❌ No boards found')
                    else:
                        print('❌ Failed to get boards')
                else:
                    print('❌ No projects found')
            else:
                print('❌ Failed to get projects')
        else:
            print('❌ No token found')
    else:
        print('❌ Login failed')
        
except Exception as e:
    print(f'❌ Error: {e}')
