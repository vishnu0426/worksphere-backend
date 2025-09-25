#!/usr/bin/env python3
"""
Simple test script to start the server and debug issues
"""
import sys
import traceback
import asyncio
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test if all imports work"""
    try:
        print("Testing imports...")
        from app.main import app
        print("✅ App imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False

def test_database():
    """Test database connection"""
    try:
        print("Testing database connection...")
        from app.core.database import engine
        print("✅ Database engine created successfully")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        traceback.print_exc()
        return False

def start_server():
    """Start the server"""
    try:
        print("Starting server...")
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Server start failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting server test...")
    
    if not test_imports():
        sys.exit(1)
    
    if not test_database():
        sys.exit(1)
    
    print("✅ All tests passed, starting server...")
    start_server()
