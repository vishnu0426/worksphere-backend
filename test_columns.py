#!/usr/bin/env python3
"""
Test columns API and structure
"""
import requests
import json

def test_columns():
    """Test the columns API to see the structure"""
    
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
            
            if token:
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                # Get the test project we created
                projects_response = requests.get('http://192.168.9.119:8000/api/v1/projects/',
                                               headers=headers)
                
                if projects_response.status_code == 200:
                    projects = projects_response.json()
                    if projects:
                        project = projects[0]
                        project_id = project.get('id')
                        print(f"📁 Project: {project.get('name')} ({project_id})")
                        
                        # Get boards
                        boards_response = requests.get(f'http://192.168.9.119:8000/api/v1/projects/{project_id}/boards',
                                                     headers=headers)
                        
                        if boards_response.status_code == 200:
                            boards = boards_response.json()
                            if boards:
                                board = boards[0]
                                board_id = board.get('id')
                                print(f"📋 Board: {board.get('name')} ({board_id})")
                                
                                # Get columns
                                columns_response = requests.get(f'http://192.168.9.119:8000/api/v1/boards/{board_id}/columns',
                                                              headers=headers)
                                
                                if columns_response.status_code == 200:
                                    columns = columns_response.json()
                                    print(f"\n📊 Found {len(columns)} columns:")
                                    
                                    for i, col in enumerate(columns):
                                        print(f"  {i+1}. ID: {col.get('id')}")
                                        print(f"     Name: {col.get('name')}")
                                        print(f"     Title: {col.get('title')}")
                                        print(f"     Position: {col.get('position')}")
                                        print(f"     Color: {col.get('color')}")
                                        print()
                                    
                                    # Test card creation with proper column
                                    if columns:
                                        first_column = columns[0]
                                        card_data = {
                                            'title': 'Frontend Test Task',
                                            'description': 'Testing task creation from frontend fix',
                                            'column_id': first_column.get('id'),
                                            'priority': 'high'
                                        }
                                        
                                        print("🎯 Testing card creation with proper column...")
                                        card_response = requests.post('http://192.168.9.119:8000/api/v1/cards/',
                                                                    json=card_data, headers=headers)
                                        print(f"Card creation status: {card_response.status_code}")
                                        
                                        if card_response.status_code in [200, 201]:
                                            card_result = card_response.json()
                                            print("✅ Card created successfully!")
                                            print(f"   Title: {card_result.get('title')}")
                                            print(f"   ID: {card_result.get('id')}")
                                            print(f"   Column: {card_result.get('column_id')}")
                                        else:
                                            print(f"❌ Card creation failed: {card_response.text}")
                                            
                                        return True
                                else:
                                    print("❌ Failed to get columns")
                            else:
                                print("❌ No boards found")
                        else:
                            print("❌ Failed to get boards")
                    else:
                        print("❌ No projects found")
                else:
                    print("❌ Failed to get projects")
            else:
                print("❌ No token found")
        else:
            print("❌ Login failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return False

if __name__ == "__main__":
    success = test_columns()
    if success:
        print("\n🎉 Column test completed successfully!")
    else:
        print("\n❌ Column test failed")
