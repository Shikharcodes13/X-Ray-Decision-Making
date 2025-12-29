"""
Start the X-Ray FastAPI server.
Run this script to start the FastAPI web server.
"""

if __name__ == '__main__':
    import uvicorn
    
    print("=" * 60)
    print("Starting X-Ray Dashboard API...")
    print("=" * 60)
    print("\nAPI will be available at: http://localhost:8000")
    print("API Docs (Swagger): http://localhost:8000/docs")
    print("API Docs (ReDoc): http://localhost:8000/redoc")
    print("\nPress Ctrl+C to stop the server\n")
    print("=" * 60)
    
    try:
        # Use import string format to enable reload properly
        # Only watch Python source directories to avoid Windows path length issues with node_modules
        import os
        import sys
        from pathlib import Path
        
        # Get the project root directory and add it to Python path
        project_root = Path(__file__).parent.resolve()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # Change to project root directory to ensure imports work correctly
        os.chdir(project_root)
        
        # Only watch Python source directories (exclude frontend/node_modules)
        reload_dirs = [
            str(project_root / "xray"),
            str(project_root / "dashboard"),
        ]
        
        uvicorn.run(
            "dashboard.app:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            reload_dirs=reload_dirs
        )
    except KeyboardInterrupt:
        print("\n\nAPI server stopped.")
    except Exception as e:
        print(f"\nError starting API server: {e}")
        import traceback
        traceback.print_exc()

