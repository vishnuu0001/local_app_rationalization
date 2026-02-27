import os
import importlib
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

load_dotenv()

db = SQLAlchemy()


def create_app(config_name=None):
    """
    Create and configure the Flask application.
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
                    If None, uses FLASK_ENV environment variable or defaults to 'development'
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Determine configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development').lower()
    
    # Load configuration from config module
    from app.config import config as config_dict
    app.config.from_object(config_dict.get(config_name, config_dict['default']))
    
    # Initialize extensions
    db.init_app(app)
    
    # CORS configuration - customize for production
    cors_origins = os.getenv('CORS_ORIGINS', '*')
    try:
        if cors_origins == '*':
            CORS(app, resources={r"/api/*": {"origins": "*"}})
        else:
            # Support comma-separated list of origins
            origins_list = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]
            if not origins_list:
                origins_list = ['*']
            CORS(app, resources={r"/api/*": {"origins": origins_list}})
    except Exception as e:
        app.logger.warning(f"Invalid CORS_ORIGINS configuration ({cors_origins}): {str(e)}. Falling back to '*'.")
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    startup_issues = []

    # Register blueprints (safe import to avoid full startup crash)
    blueprint_modules = [
        ('app.routes.upload_bp', 'bp'),
        ('app.routes.analysis_bp', 'bp'),
        ('app.routes.visualization_bp', 'bp'),
        ('app.routes.correlation_bp', 'correlation_bp'),
        ('app.routes.capability_bp', 'capability_bp'),
    ]

    for module_name, blueprint_attr in blueprint_modules:
        try:
            module = importlib.import_module(module_name)
            app.register_blueprint(getattr(module, blueprint_attr))
        except Exception as e:
            issue = f"Blueprint load failed for {module_name}.{blueprint_attr}: {str(e)}"
            startup_issues.append(issue)
            app.logger.error(issue)
    
    # Create database tables and handle initialization
    with app.app_context():
        try:
            # Import all models to register them with SQLAlchemy
            from app.models import (
                infrastructure, code, application, pdf_report,
                correlation, analysis, capability, cast, corent_data
            )
            
            db.create_all()
            app.logger.info(f"Database initialized successfully")
            app.logger.info(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        except Exception as e:
            issue = f"Database initialization failed: {str(e)}"
            startup_issues.append(issue)
            app.logger.error(issue)
            app.logger.warning("Continuing startup without blocking app initialization")
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        try:
            # Test database connection
            db.session.execute(text('SELECT 1'))
            db_status = 'connected'
        except Exception as e:
            db_status = f'disconnected: {str(e)}'
        
        return {
            'status': 'healthy',
            'service': 'Infrastructure Assessment API',
            'database': db_status,
            'environment': os.getenv('FLASK_ENV', 'development'),
            'database_type': os.getenv('DATABASE_PROVIDER', 'sqlite'),
            'startup_issues': startup_issues,
        }, 200
    
    # Shutdown handler for graceful cleanup
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Clean up database session"""
        if exception and app.config['DEBUG']:
            app.logger.error(f"Application error: {str(exception)}")
    
    return app
