from flask import Blueprint, request, jsonify, current_app, url_for
from flask_wtf.csrf import generate_csrf
from werkzeug.utils import secure_filename
import os

from app.models.settings import Settings
from app.models.file_share import FileShare
from app.utils.email import get_mailjet_client

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.before_request
def require_api_key():
    """Authenticate all /api requests with X-API-Key."""
    api_key = request.headers.get('X-API-Key', '')
    if not api_key or api_key != Settings.get_api_key():
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401


@api_bp.route('/csrf', methods=['GET'])
def api_csrf():
    """Return a CSRF token for subsequent mutating API requests."""
    return jsonify({'csrf_token': generate_csrf()}), 200


@api_bp.route('/upload', methods=['POST'])
def upload_api():
    """Handle external API file uploads"""
    files = request.files.getlist('files')
    if not files or not any(f.filename for f in files):
        return jsonify({'success': False, 'error': 'No files uploaded'}), 400

    # Create share with no recipient
    retention = Settings.get('file_retention_hours', 24)
    share = FileShare.create('', [], retention)

    # Save uploaded files
    uploads_dir = current_app.config.get('UPLOAD_FOLDER')
    share_dir = os.path.join(uploads_dir, share.token)
    os.makedirs(share_dir, exist_ok=True)

    saved = []
    for f in files:
        if not f.filename:
            continue
        filename = secure_filename(f.filename)
        path = os.path.join(share_dir, filename)
        f.save(path)
        saved.append(filename)

    share.files = saved
    share.save()

    # Notify admin if email configured
    admin_email = Settings.get_notification_email()
    if admin_email:
        client = get_mailjet_client()
        if client:
            # Send simple notification email to admin
            from_email = Settings.get_email_config().get('from_email')
            from_name = Settings.get_email_config().get('from_name')
            # Link to admin files listing
            admin_files_url = url_for('admin.files', _external=True)
            # Build file list HTML and text
            file_list_items = ''.join(f'<li>{fname}</li>' for fname in saved)
            text_files_list = '\n'.join(saved)
            data = {
                'Messages': [
                    {
                        'From': {'Email': from_email, 'Name': from_name},
                        'To': [{'Email': admin_email, 'Name': admin_email}],
                        'Subject': 'New files uploaded to Secure File Share App – Action Required',
                        'TextPart': f'A new file upload has occurred.\n\nFiles:\n{text_files_list}\n\nView all shares: {admin_files_url}',
                        'HTMLPart': f'''<h3>New files uploaded via API</h3>
<p>Action Required: Review the new files in your admin console.</p>
<ul>{file_list_items}</ul>
<p><a href="{admin_files_url}">Go to All File Shares</a></p>'''
                    }
                ]
            }
            try:
                client.send.create(data=data)
            except Exception:
                current_app.logger.exception("API notification email failed")

    # Return share token
    return jsonify({'success': True, 'token': share.token}), 200
