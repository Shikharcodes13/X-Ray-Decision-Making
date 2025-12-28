"""
Start the X-Ray dashboard server.
Run this script to start the Flask web server.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from xray.dashboard.app import app

if __name__ == '__main__':
    print("=" * 60)
    print("Starting X-Ray Dashboard...")
    print("=" * 60)
    print("\nDashboard will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server\n")
    print("=" * 60)
    
    try:
        app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\nDashboard server stopped.")
    except Exception as e:
        print(f"\nError starting dashboard: {e}")
        import traceback
        traceback.print_exc()

