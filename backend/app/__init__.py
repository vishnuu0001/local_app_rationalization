import os
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
    if cors_origins == '*':
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    else:
        # Support comma-separated list of origins
        origins_list = [origin.strip() for origin in cors_origins.split(',')]
        CORS(app, resources={r"/api/*": {"origins": origins_list}})
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from app.routes import upload_bp, analysis_bp, visualization_bp, correlation_bp, capability_bp
    app.register_blueprint(upload_bp.bp)
    app.register_blueprint(analysis_bp.bp)
    app.register_blueprint(visualization_bp.bp)
    app.register_blueprint(correlation_bp.correlation_bp)
    app.register_blueprint(capability_bp.capability_bp)
    
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
            app.logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
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
            'database_type': os.getenv('DATABASE_PROVIDER', 'sqlite')
        }, 200
    
    # Shutdown handler for graceful cleanup
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Clean up database session"""
        if exception and app.config['DEBUG']:
            app.logger.error(f"Application error: {str(exception)}")
    
    return app
