"""
Netlify Serverless Function Handler
=====================================
This file handles Netlify Functions deployment.
"""

import sys
import os

# Add parent directories to path for imports
FUNCTION_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(FUNCTION_DIR))
sys.path.insert(0, PROJECT_ROOT)

from api.app import app

# Netlify Functions Handler
try:
    import serverless_wsgi
    
    def handler(event, context):
        """
        Netlify Functions handler that wraps the Flask app
        using serverless-wsgi for AWS Lambda compatibility.
        """
        return serverless_wsgi.handle_request(app, event, context)
        
except ImportError:
    def handler(event, context):
        return {
            'statusCode': 500,
            'body': 'serverless-wsgi not installed'
        }


if __name__ == '__main__':
    # For local testing of Netlify function
    from config.settings import PORT
    print(f"\n🚀 Starting Netlify function locally at: http://localhost:{PORT}")
    app.run(debug=True, port=PORT)
