"""Configuration for Flask application with dynamic database support"""

import os
from datetime import timedelta


def get_database_uri():
    """
    Dynamically configure database URI based on DATABASE_PROVIDER environment variable.
    Supports: sqlite (default), postgresql
    """
    db_provider = os.getenv('DATABASE_PROVIDER', 'sqlite').lower()
    
    if db_provider == 'postgresql':
        # PostgreSQL configuration
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            raise ValueError(
                "DATABASE_PROVIDER is set to 'postgresql' but DATABASE_URL is not configured. "
                "Set DATABASE_URL to your PostgreSQL connection string (e.g., postgresql://user:pass@host:5432/dbname)"
            )
        
        # Ensure proper SQLAlchemy driver for PostgreSQL
        if db_url.startswith('postgresql://'):
            # Check if psycopg2 driver is specified
            if 'psycopg2' not in db_url:
                db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://')
        elif db_url.startswith('postgres://'):
            # Handle deprecated postgres:// scheme
            db_url = db_url.replace('postgres://', 'postgresql+psycopg2://')
        
        return db_url
    
    else:
        # SQLite configuration (default)
        # Check for environment-specific paths
        if 'DATABASE_PATH' in os.environ:
            # Use custom path (only if non-empty)
            db_path = os.getenv('DATABASE_PATH', '').strip()
            if db_path:
                return f'sqlite:///{db_path}'
        
        # Default paths based on environment
        env = os.getenv('FLASK_ENV', 'development').lower()

        if env == 'testing':
            # In-memory database for tests
            return 'sqlite:///:memory:'
        else:
            # Development and production (IIS): store in instance folder
            instance_path = os.path.join(os.path.dirname(__file__), '..', 'instance')
            os.makedirs(instance_path, exist_ok=True)
            db_file = os.path.join(instance_path, 'infra_assessment.db')
            return f'sqlite:///{db_file}'


def get_sqlalchemy_options():
    """Get SQLAlchemy engine options based on database type"""
    db_provider = os.getenv('DATABASE_PROVIDER', 'sqlite').lower()
    
    base_options = {
        'pool_pre_ping': True,  # Test connections before using
    }
    
    if db_provider == 'postgresql':
        # Connection pooling for PostgreSQL
        base_options.update({
            'pool_size': int(os.getenv('SQLALCHEMY_POOL_SIZE', 5)),
            'pool_recycle': int(os.getenv('SQLALCHEMY_POOL_RECYCLE', 60)),
            'max_overflow': int(os.getenv('SQLALCHEMY_MAX_OVERFLOW', 10)),
        })
    else:
        # SQLite options: avoid QueuePool-specific args to stay compatible
        # across SQLAlchemy versions and serverless runtimes.
        base_options.update({
            'connect_args': {'check_same_thread': False},
        })
    
    return base_options


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-secret-key-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    _default_upload_folder = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '').strip() or os.path.abspath(_default_upload_folder)
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 52428800))  # 50MB
    JSONIFY_PRETTYPRINT_REGULAR = True
    JSON_SORT_KEYS = False
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_ENGINE_OPTIONS = get_sqlalchemy_options()
    
    # Security defaults
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() in ('1', 'true', 'yes')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_REFRESH_EACH_REQUEST = True


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration (IIS, Windows Server)"""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args': {'check_same_thread': False},
    }


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
