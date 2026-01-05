"""
Flask Application Factory
==========================
Creates and configures the Flask application.
"""

from flask import Flask, render_template
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SECRET_KEY, DEBUG


def create_app():
    """Application factory pattern"""
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_folder = os.path.join(project_root, 'frontend', 'templates')
    static_folder = os.path.join(project_root, 'frontend', 'static')
    
    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder
    )
    
    app.secret_key = SECRET_KEY
    app.debug = DEBUG
    
    # Register blueprints
    from api.routes.travel import travel_bp
    app.register_blueprint(travel_bp)
    
    # Home route
    @app.route('/')
    def index():
        """Render the main page"""
        return render_template('index.html')
    
    return app


# Create the app instance
app = create_app()
