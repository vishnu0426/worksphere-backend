#!/usr/bin/env python3
"""
Create a test project with boards and columns for testing
"""
import requests
import json

def create_test_project():
    """Create test project with kanban board and columns"""
    
    # Login
    login_data = {
        'email': 'owner@agnoworksphere.com',
        'password': 'OwnerPass123!'
    }
    
    try:
        print("🔐 Logging in...")
        login_response = requests.post('http://192.168.9.119:8000/api/v1/auth/login', 
                                     json=login_data)
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            token = login_result.get('tokens', {}).get('access_token')
            organization_id = login_result.get('organization', {}).get('id')
            
            if token and organization_id:
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                print(f'🏢 Organization ID: {organization_id}')
                
                # Create a test project
                project_data = {
                    'name': 'Test Project',
                    'description': 'A test project for kanban board testing'
                }

                print("📁 Creating project...")
                project_response = requests.post(f'http://192.168.9.119:8000/api/v1/projects/?organization_id={organization_id}',
                                               json=project_data, headers=headers)
                print(f'Project creation status: {project_response.status_code}')
                
                if project_response.status_code in [200, 201]:
                    project_result = project_response.json()
                    project_id = project_result.get('id')
                    print(f'✅ Project created: {project_id}')
                    
                    if project_id:
                        # Create a board for this project
                        board_data = {
                            'name': 'Main Board',
                            'description': 'Main kanban board for the project',
                            'project_id': project_id
                        }
                        
                        print("📋 Creating board...")
                        board_response = requests.post(f'http://192.168.9.119:8000/api/v1/projects/{project_id}/boards',
                                                     json=board_data, headers=headers)
                        print(f'Board creation status: {board_response.status_code}')
                        
                        if board_response.status_code in [200, 201]:
                            board_result = board_response.json()
                            board_id = board_result.get('id')
                            print(f'✅ Board created: {board_id}')
                            
                            if board_id:
                                # Create columns for this board
                                columns_to_create = [
                                    {'name': 'To-Do', 'color': '#E5E7EB', 'position': 0},
                                    {'name': 'In Progress', 'color': '#3B82F6', 'position': 1},
                                    {'name': 'Review', 'color': '#F59E0B', 'position': 2},
                                    {'name': 'Done', 'color': '#10B981', 'position': 3}
                                ]
                                
                                print("📊 Creating columns...")
                                created_columns = []
                                for column_data in columns_to_create:
                                    column_response = requests.post(f'http://192.168.9.119:8000/api/v1/boards/{board_id}/columns',
                                                                  json=column_data, headers=headers)
                                    print(f'Column "{column_data["name"]}" creation status: {column_response.status_code}')
                                    
                                    if column_response.status_code in [200, 201]:
                                        column_result = column_response.json()
                                        created_columns.append(column_result)
                                        print(f'✅ Column created: {column_result.get("name")} (ID: {column_result.get("id")})')
                                    else:
                                        print(f'❌ Column creation failed: {column_response.text[:200]}')
                                
                                print(f'\n🎉 Setup complete!')
                                print(f'   Project ID: {project_id}')
                                print(f'   Board ID: {board_id}')
                                print(f'   Columns created: {len(created_columns)}')
                                
                                # Test card creation with first column
                                if created_columns:
                                    first_column = created_columns[0]
                                    card_data = {
                                        'title': 'Test Task',
                                        'description': 'A test task to verify card creation',
                                        'column_id': first_column.get('id'),
                                        'priority': 'medium'
                                    }
                                    
                                    print("\n🎯 Testing card creation...")
                                    card_response = requests.post('http://192.168.9.119:8000/api/v1/cards/',
                                                                json=card_data, headers=headers)
                                    print(f'Card creation status: {card_response.status_code}')
                                    
                                    if card_response.status_code in [200, 201]:
                                        card_result = card_response.json()
                                        print(f'✅ Card created: {card_result.get("title")} (ID: {card_result.get("id")})')
                                    else:
                                        print(f'❌ Card creation failed: {card_response.text[:200]}')
                                        
                                return True
                            else:
                                print('❌ No board ID returned')
                        else:
                            print(f'❌ Board creation failed: {board_response.text[:200]}')
                    else:
                        print('❌ No project ID returned')
                else:
                    print(f'❌ Project creation failed: {project_response.text[:200]}')
            else:
                print('❌ Missing token or organization ID')
        else:
            print(f'❌ Login failed: {login_response.text[:200]}')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        return False
    
    return False

if __name__ == "__main__":
    success = create_test_project()
    if success:
        print("\n🎉 Test project setup completed successfully!")
    else:
        print("\n❌ Test project setup failed")
