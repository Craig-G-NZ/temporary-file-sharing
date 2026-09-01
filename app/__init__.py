from flask import Flask, render_template, request, flash, g
import pytz
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from logging.handlers import RotatingFileHandler
import os
import logging
import secrets

from app.utils.helpers import DEFAULT_TIMEZONE


def _resolve_config_name(config_name):
    if config_name is not None:
        return config_name
    if os.path.exists('/.dockerenv') or os.path.exists('/app/.dockerenv'):
        return 'production'
    return 'development'


def _resolve_secret_key(config_name):
    secret_key = os.environ.get('SECRET_KEY')
    if secret_key:
        return secret_key
    if config_name == 'production':
        raise RuntimeError('SECRET_KEY environment variable must be set in production')
    return secrets.token_hex(32)


def _resolve_directories(config_name):
    if config_name == 'production':
        return '/app/uploads', '/app/data', '/app/logs'
    base = os.path.abspath(os.path.dirname(__file__))
    return (
        os.path.join(base, 'uploads'),
        os.path.join(base, 'data'),
        os.path.join(base, 'logs'),
    )


def _configure_app(app, config_name):
    app.config['DEBUG'] = config_name == 'development'
    app.config['SECRET_KEY'] = _resolve_secret_key(config_name)
    app.config['WTF_CSRF_TIME_LIMIT'] = None
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024

    uploads_dir, data_dir, logs_dir = _resolve_directories(config_name)
    app.config['UPLOAD_FOLDER'] = uploads_dir
    app.config['DATA_FOLDER'] = data_dir
    app.config['LOG_FOLDER'] = logs_dir
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)


def _add_rotating_handler(app, filename, level, backup_count):
    handler = RotatingFileHandler(
        os.path.join(app.config['LOG_FOLDER'], filename),
        maxBytes=10240000,
        backupCount=backup_count,
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(level)
    app.logger.addHandler(handler)


def _configure_logging(app):
    if app.debug:
        return
    _add_rotating_handler(app, 'downloads.log', logging.INFO, 5)
    _add_rotating_handler(app, 'app.log', logging.WARNING, 3)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Secure File Share application startup')


def _setup_login(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.admin import Admin
        return Admin.get(user_id)


def _setup_request_hooks(app):
    @app.before_request
    def before_request():
        g.pytz = pytz
        g.nz_tz = pytz.timezone(DEFAULT_TIMEZONE)

    @app.before_request
    def check_configuration():
        from app.models.settings import Settings

        endpoint = request.endpoint
        if not endpoint or endpoint.startswith(('static', 'auth.')) or endpoint == 'main.index':
            return
        if endpoint.startswith('admin.') and current_user.is_authenticated:
            g.is_fully_configured = Settings.is_configured()
            g.admin_exists = True


def _file_exists_filter(file_path):
    try:
        return os.path.exists(file_path) if file_path else False
    except OSError:
        return False


def _file_size_filter(file_path):
    try:
        return os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
    except OSError:
        return 0


def _format_file_size_filter(bytes_size):
    from app.utils.helpers import format_file_size
    return format_file_size(bytes_size)


def _format_datetime_filter(dt):
    if dt is None:
        return 'Never'
    try:
        from datetime import datetime
        from app.utils.helpers import format_datetime_user_timezone

        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        return format_datetime_user_timezone(dt)
    except (TypeError, ValueError, OSError, AttributeError):
        return str(dt)


def _time_ago_filter(dt):
    if dt is None:
        return 'Never'
    try:
        from datetime import datetime
        from app.utils.helpers import as_utc, utc_now

        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)

        diff = utc_now() - as_utc(dt)
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        if diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        if diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        return "Just now"
    except (TypeError, ValueError, OSError, AttributeError):
        return str(dt)


def _register_template_filters(app):
    app.add_template_filter(_file_exists_filter, 'file_exists')
    app.add_template_filter(_file_size_filter, 'file_size')
    app.add_template_filter(_format_file_size_filter, 'format_file_size')
    app.add_template_filter(_format_datetime_filter, 'format_datetime')
    app.add_template_filter(_time_ago_filter, 'time_ago')


def _register_blueprints(app):
    from app.web.main import main_bp
    from app.web.auth import auth_bp
    from app.web.admin import admin_bp
    from app.web.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        flash('File too large! Please check the maximum upload size in settings.', 'error')
        return render_template('errors/413.html'), 413

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error('Server Error: %s', error)
        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.exception('Unhandled Exception: %s', error)
        return render_template('errors/500.html'), 500


def _start_cleanup_scheduler(app):
    from app.utils.cleanup import cleanup_scheduler
    cleanup_scheduler.init_app(app)
    with app.app_context():
        cleanup_scheduler.start()


def create_app(config_name=None):
    config_name = _resolve_config_name(config_name)
    app = Flask(__name__)
    app.config['WTF_CSRF_ENABLED'] = True
    CSRFProtect(app)
    _configure_app(app, config_name)
    _configure_logging(app)
    initialize_database()
    run_security_migrations()
    _setup_login(app)
    _setup_request_hooks(app)
    _register_template_filters(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _start_cleanup_scheduler(app)
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
            # Create a default admin using ADMIN_PASSWORD env var if provided, otherwise use a secure temporary password
            default_password = os.environ.get('ADMIN_PASSWORD') or "SecureTemp123!@#"
            Admin.create_or_update('admin', default_password)
            if os.environ.get('ADMIN_PASSWORD'):
                print("INFO: Default admin created (username: admin) - password sourced from ADMIN_PASSWORD environment variable.")
                print("INFO: ⚠️  SECURITY WARNING: Ensure the ADMIN_PASSWORD is changed to a strong secret in production.")
            else:
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
