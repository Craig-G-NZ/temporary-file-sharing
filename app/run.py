import os
from app import create_app

# Get the environment configuration from the FLASK_ENV environment variable.
# This allows for easy switching between 'development' and 'production' modes.
# It defaults to 'production' for safety if the variable is not set.
config_name = os.getenv('FLASK_ENV', 'production')

# Create the Flask app instance using the factory function from app/__init__.py
app = create_app(config_name)
# app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB
app.config['MAX_CONTENT_LENGTH'] = None  # No file size limit as requested

if __name__ == '__main__':
    # The built-in Flask development server is used here.
    # For a production environment, a more robust WSGI server like Gunicorn or uWSGI should be used.
    # The host '0.0.0.0' makes the server accessible from other devices on the network.
    app.run(host='0.0.0.0', port=5000)