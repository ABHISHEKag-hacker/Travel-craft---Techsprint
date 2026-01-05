"""
Travel Planner Application - Entry Point
==========================================
Run this file to start the Flask development server.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.app import app
from config.settings import PORT, DEBUG


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌍 TRAVEL PLANNER - WEB INTERFACE 🌍".center(60))
    print("="*60)
    print(f"\n🚀 Starting server at: http://localhost:{PORT}")
    print("📝 Open this URL in your browser to use the Travel Planner")
    print("\nPress CTRL+C to stop the server\n")
    
    app.run(debug=DEBUG, port=PORT, host='0.0.0.0')
