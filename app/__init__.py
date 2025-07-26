from flask import Flask, app, render_template, request, redirect, url_for, flash, g
import pytz
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from logging.handlers import RotatingFileHandler
import os
import logging

# def create_app(config_name='development'):
def create_app(config_name=None):
    # Auto-select config: production if running in Docker, else development
    if config_name is None:
        if os.path.exists('/.dockerenv') or os.path.exists('/app/.dockerenv'):
            config_name = 'production'
        else:
            config_name = 'development'
    
    app = Flask(__name__)
    
    # Configuration
    if config_name == 'development':
        app.config['DEBUG'] = True
        app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    else:
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'lkejr2io43j509tguw09a4u5oiq34ntog8ye7tq34ithgoisyo8g7qo4oighq3i4houdgo7o97')
    
    # Configure CSRF token timeout (disable expiration)
    app.config['WTF_CSRF_TIME_LIMIT'] = None
    # Large file upload support (10GB max)
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB max upload
    
    if config_name == 'production':
        # Force absolute paths for directories
        uploads_dir = '/app/uploads'
        data_dir = '/app/data'
        logs_dir = '/app/logs'
    else:
        # Force absolut path for directories
        uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
        logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'logs'))

    app.config['UPLOAD_FOLDER'] = uploads_dir
    app.config['DATA_FOLDER'] = data_dir
    app.config['LOG_FOLDER'] = logs_dir

    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Ensure upload directory exists
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    
    # Set up timezone handling
    @app.before_request
    def before_request():
        g.pytz = pytz
        g.nz_tz = pytz.timezone('Pacific/Auckland')

    # Configure detailed logging
    if not app.debug:
        # File handler for download logs
        download_handler = RotatingFileHandler(
            os.path.join(app.config['LOG_FOLDER'], 'downloads.log'), 
            maxBytes=10240000,  # 10MB
            backupCount=5
        )
        download_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        download_handler.setLevel(logging.INFO)
        app.logger.addHandler(download_handler)
        
        # File handler for application logs
        app_handler = RotatingFileHandler(
            os.path.join(app.config['LOG_FOLDER'], 'app.log'), 
            maxBytes=10240000,  # 10MB
            backupCount=3
        )
        app_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app_handler.setLevel(logging.WARNING)
        app.logger.addHandler(app_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Secure File Share application startup')
    
    # Initialize database on first run
    initialize_database()
    
    # Run security migrations
    run_security_migrations()
    
    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.admin import Admin
        return Admin.get(user_id)
    
    # Configuration check middleware
    @app.before_request
    def check_configuration():
        from app.models.settings import Settings
        from flask_login import current_user
        
        # Skip check for static files and auth routes
        if (request.endpoint and 
            (request.endpoint.startswith('static') or 
             request.endpoint.startswith('auth.') or
             request.endpoint == 'main.index')):
            return
        
        # Check if app is configured and user is trying to access admin area
        if (request.endpoint and request.endpoint.startswith('admin.') and 
            current_user.is_authenticated):
            
            # Store configuration status in g for templates
            g.is_fully_configured = Settings.is_configured()
            g.admin_exists = True  # We know user is logged in
    
    # Add template filters for file handling
    @app.template_filter('file_exists')
    def file_exists_filter(file_path):
        """Check if file exists"""
        try:
            return os.path.exists(file_path) if file_path else False
        except:
            return False
    
    @app.template_filter('file_size')
    def file_size_filter(file_path):
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
        except:
            return 0
    
    @app.template_filter('format_file_size')
    def format_file_size_filter(bytes_size):
        """Format file size in human readable format"""
        from app.utils.helpers import format_file_size
        return format_file_size(bytes_size)
    
    @app.template_filter('format_datetime')
    def format_datetime_filter(dt):
        """Format datetime for display in user's timezone"""
        if dt is None:
            return 'Never'
        try:
            from datetime import datetime
            from app.utils.helpers import format_datetime_user_timezone
            
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt)
            
            return format_datetime_user_timezone(dt)
        except:
            return str(dt)
    
    @app.template_filter('time_ago')
    def time_ago_filter(dt):
        """Show time ago format"""
        if dt is None:
            return 'Never'
        try:
            from datetime import datetime
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt)
            
            now = datetime.utcnow()
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "Just now"
        except:
            return str(dt)
    
    # Register blueprints
    from app.web.main import main_bp
    from app.web.auth import auth_bp
    from app.web.admin import admin_bp
    from app.web.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Exempt API routes from CSRF
    csrf.exempt(api_bp)
    csrf.exempt(app.view_functions['admin.upload_chunk'])
    csrf.exempt(app.view_functions['admin.request_share_token'])
    csrf.exempt(app.view_functions['admin.finalize_share'])

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        flash('File too large! Please check the maximum upload size in settings.', 'error')
        return render_template('errors/413.html'), 413
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f'Unhandled Exception: {error}', exc_info=True)
        return render_template('errors/500.html'), 500
    
    # Initialize cleanup scheduler
    from app.utils.cleanup import cleanup_scheduler
    cleanup_scheduler.init_app(app)
    
    # Start scheduler after app setup (Flask 2.2+ compatible)
    with app.app_context():
        cleanup_scheduler.start()
    
    return app

def run_security_migrations():
    """Run security-related database migrations"""
    try:
        from app.models.settings import Settings
        
        print("INFO: Running security migrations...")
        
        # Migrate sensitive settings to encrypted storage
        sensitive_keys = ['mailjet_api_key', 'mailjet_api_secret', 'api_key']
        
        for key in sensitive_keys:
            try:
                Settings.migrate_to_encrypted(key)
            except Exception as e:
                print(f"WARNING: Failed to migrate {key}: {e}")
        
        print("INFO: Security migrations completed successfully")
        
    except Exception as e:
        print(f"ERROR: Security migration failed: {e}")
        import traceback
        traceback.print_exc()

def initialize_database():
    """Initialize database tables and default settings on first run"""
    try:
        from app.utils.database import init_database
        from app.models.admin import Admin
        from app.models.settings import Settings
        from app.models.file_share import FileShare
        
        # Initialize all database tables
        init_database()
        
        # Initialize FileShare table with new schema
        FileShare.init_db()
        
        # Upgrade database schema if needed
        try:
            FileShare.upgrade_db_schema()
        except Exception as e:
            print(f"Schema upgrade info: {e}")
        
        # Create default admin if none exists
        if not Admin.exists():
            # Create a default admin with secure temporary credentials
            default_password = "SecureTemp123!@#"
            Admin.create_or_update('admin', default_password)
            print("INFO: Default admin created (username: admin, password: SecureTemp123!@#)")
            print("INFO: ⚠️  SECURITY WARNING: Please login immediately and change these credentials!")
            
            # Set flag that initial setup is needed
            Settings.set('needs_initial_setup', True, 'Indicates if initial setup is required')
        
        # Set default app settings if they don't exist (UPDATED FOR GB)
        default_settings = [
            ('file_retention_hours', 24, 'File retention period in hours'),
            ('max_file_size_gb', 5, 'Maximum file size in GB'),
            ('max_total_upload_gb', 20, 'Maximum total upload size in GB'),
            ('max_files_per_upload', 10, 'Maximum files per upload'),
            ('require_email', True, 'Require email for file sharing'),
            ('auto_cleanup', True, 'Automatic cleanup of expired files'),
            ('cleanup_interval_minutes', 60, 'Cleanup interval in minutes'),
            ('mailjet_from_name', 'Secure File Share', 'Default from name for emails'),
        ]
        
        for key, default_value, description in default_settings:
            if not Settings.get(key):
                Settings.set(key, default_value, description)
        
        print("INFO: Database initialization completed successfully")
        
    except Exception as e:
        print(f"ERROR: Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
