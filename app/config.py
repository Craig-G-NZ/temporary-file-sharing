import os
from datetime import timedelta

class Config:
    # SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    # MAX_CONTENT_LENGTH = None  # No file size limit as requested

    # Mailjet configuration
    MAILJET_API_KEY = os.environ.get('MAILJET_API_KEY')
    MAILJET_API_SECRET = os.environ.get('MAILJET_API_SECRET')
    MAILJET_FROM_EMAIL = os.environ.get('MAILJET_FROM_EMAIL')
    MAILJET_FROM_NAME = os.environ.get('MAILJET_FROM_NAME') or 'File Share'

    # Admin credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'changeme'

    # File retention
    FILE_RETENTION_HOURS = int(os.environ.get('FILE_RETENTION_HOURS') or '24')

    # App settings
    WTF_CSRF_TIME_LIMIT = None  # No CSRF timeout

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
