import os
import importlib
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, make_response, jsonify, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Use absolute path so load_dotenv works regardless of working directory (e.g. IIS FastCGI)
_env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=_env_path, override=False)

db = SQLAlchemy()

# Allowed CORS origins — production domains are ALWAYS included.
# Any extra origins in the CORS_ORIGINS env var are merged on top.
_CORS_PRODUCTION_ORIGINS = {
    'https://stratapp.org',
    'https://www.stratapp.org',
}
_CORS_LOCALHOST_ORIGINS = {
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:3001',
    'http://127.0.0.1:3001',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:4173',
    'http://127.0.0.1:4173',
}
_CORS_ALLOWED_ORIGINS = (
    _CORS_PRODUCTION_ORIGINS
    | _CORS_LOCALHOST_ORIGINS
    | {
        o.strip()
        for o in os.getenv('CORS_ORIGINS', '').split(',')
        if o.strip() and o.strip() != '*'
    }
)

_CORS_ALLOW_HEADERS = (
    'Content-Type, Authorization, Accept, X-Requested-With, Origin, Cache-Control'
)
_CORS_ALLOW_METHODS = 'GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD'


DEFAULT_LOCAL_CORS_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:3001',
    'http://127.0.0.1:3001',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:4173',
    'http://127.0.0.1:4173',
]


PUBLIC_API_PATHS = {
    '/api/health',
    '/health',
    '/api/auth/login',
    '/api/auth/apps',
    '/api/auth/oauth/providers',
    '/api/auth/google/start',
    '/api/auth/google/callback',
    '/api/auth/github/start',
    '/api/auth/github/callback',
}


def _resolve_cors_origins(raw_origins, include_local_defaults=True):
    """Resolve CORS origins from env and include safe localhost defaults."""
    if not raw_origins:
        return DEFAULT_LOCAL_CORS_ORIGINS if include_local_defaults else '*'

    normalized_value = raw_origins.strip()
    if normalized_value == '*':
        return '*'

    configured_origins = [origin.strip() for origin in normalized_value.split(',') if origin.strip()]
    if include_local_defaults:
        merged_origins = configured_origins + [
            origin for origin in DEFAULT_LOCAL_CORS_ORIGINS
            if origin not in configured_origins
        ]
    else:
        merged_origins = configured_origins

    if merged_origins:
        return merged_origins

    return DEFAULT_LOCAL_CORS_ORIGINS if include_local_defaults else '*'


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

    # ------------------------------------------------------------------ #
    #  CORS — three independent layers so the header is ALWAYS emitted    #
    #  even if one layer fails under IIS / wfastcgi.                      #
    # ------------------------------------------------------------------ #

    # Layer 1: Flask-CORS — uses the same authoritative set as layers 2 & 3
    _cors_kwargs = {
        'supports_credentials': False,
        'allow_headers': [
            'Content-Type', 'Authorization', 'Accept',
            'X-Requested-With', 'Origin', 'Cache-Control'
        ],
        'methods': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'],
        'expose_headers': ['Content-Disposition', 'Content-Length'],
        'max_age': 600,
        'send_wildcard': False,
    }
    # Layer 1: Flask-CORS — uses the same authoritative set as layers 2 & 3
    try:
        CORS(app, resources={r"/*": {"origins": list(_CORS_ALLOWED_ORIGINS)}}, **_cors_kwargs)
    except Exception as e:
        app.logger.warning(f"CORS init error ({e}). Falling back to '*'.")
        CORS(app, resources={r"/*": {"origins": "*"}}, **_cors_kwargs)

    # Layer 2: Direct after_request hook — writes the header ourselves.
    # This bypasses Flask-CORS internals entirely and is guaranteed to run
    # for every response that leaves Flask, including under IIS/wfastcgi.
    @app.after_request
    def _apply_cors(response):
        origin = request.headers.get('Origin', '')
        if origin in _CORS_ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Headers'] = _CORS_ALLOW_HEADERS
            response.headers['Access-Control-Allow-Methods'] = _CORS_ALLOW_METHODS
            response.headers['Vary'] = 'Origin'
        return response

    # Layer 3: OPTIONS preflight — respond immediately with 200 so the
    # browser's preflight check never hits a 405 or falls through to Flask.
    @app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
    @app.route('/<path:path>', methods=['OPTIONS'])
    def _options_preflight(path):
        response = make_response('', 200)
        origin = request.headers.get('Origin', '')
        if origin in _CORS_ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Headers'] = _CORS_ALLOW_HEADERS
            response.headers['Access-Control-Allow-Methods'] = _CORS_ALLOW_METHODS
            response.headers['Access-Control-Max-Age'] = '600'
            response.headers['Vary'] = 'Origin'
        return response

    @app.before_request
    def _authenticate_api_requests():
        if request.method == 'OPTIONS':
            return None

        path = request.path or ''
        if not path.startswith('/api'):
            return None

        if path in PUBLIC_API_PATHS:
            return None

        try:
            from app.models.auth import APP_RATIONALIZATION
            from app.services.auth_service import AuthService

            token = AuthService.extract_bearer_token(request.headers.get('Authorization', ''))
            if not token:
                return jsonify({'error': 'Authentication required'}), 401

            auth = AuthService.validate_access_token(token, check_session=True)
            if not auth['ok']:
                return jsonify({'error': auth['error']}), auth['status']

            g.current_user = auth['user']
            g.current_apps = auth['apps']
            g.current_token_payload = auth['payload']

            if not path.startswith('/api/auth'):
                if auth['user'].role != 'admin' and APP_RATIONALIZATION not in auth['apps']:
                    return jsonify({'error': 'Access denied for App Rationalization'}), 403

        except Exception as e:
            app.logger.error(f'Authentication middleware error: {str(e)}')
            return jsonify({'error': 'Authentication failed'}), 401

        return None
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    startup_issues = []

    # Register blueprints (safe import to avoid full startup crash)
    blueprint_modules = [
        ('app.routes.auth_bp', 'auth_bp'),
        ('app.routes.upload_bp', 'bp'),
        ('app.routes.analysis_bp', 'bp'),
        ('app.routes.visualization_bp', 'bp'),
        ('app.routes.correlation_bp', 'correlation_bp'),
        ('app.routes.capability_bp', 'capability_bp'),
        ('app.routes.golden_data_bp', 'golden_data_bp'),
        ('app.routes.reset_bp', 'reset_bp'),
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
                correlation, analysis, capability, cast, corent_data,
                industry_data, consolidated_app, golden_data,
                predicted_analysis, correlation_workspace, auth,
            )
            
            db.create_all()
            try:
                from app.services.auth_service import AuthService

                AuthService.ensure_default_admin()
                app.logger.info('Default authentication admin user ensured')
            except Exception as e:
                startup_issues.append(f'Auth bootstrap failed: {str(e)}')
                app.logger.error(f'Auth bootstrap failed: {str(e)}')

            app.logger.info(f"Database initialized successfully")
            app.logger.info(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

            # ── Incremental column migrations ─────────────────────────────
            # SQLAlchemy's create_all() won't add new columns to existing
            # tables.  Perform safe ALTER TABLE … ADD COLUMN here so that
            # the DB schema stays in sync with the models on every restart.
            _incremental_migrations = [
                "ALTER TABLE workspace_runs ADD COLUMN source_files_hash VARCHAR(64)",
            ]
            with db.engine.connect() as _mc:
                for _sql in _incremental_migrations:
                    try:
                        _mc.execute(text(_sql))
                        _mc.commit()
                    except Exception:
                        pass  # column already exists — safe to ignore
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
