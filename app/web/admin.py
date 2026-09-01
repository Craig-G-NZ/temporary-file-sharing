from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.utils import secure_filename
from app.models.admin import Admin
from app.models.settings import Settings
from app.models.file_share import FileShare
from app.utils.helpers import DEFAULT_TIMEZONE, safe_join_path, safe_next_url, utc_now
import os
import re
import shutil
import tempfile

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

_FILE_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,200}$')
_CHUNK_NAME_RE = re.compile(r'^chunk_\d{5}$')
_MAX_CHUNKS = 4096
ADMIN_FILES_ENDPOINT = 'admin.files'
FILE_SHARE_NOT_FOUND = 'File share not found!'

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        admin = Admin.authenticate(username, password)
        if admin:
            login_user(admin, remember=True)
            flash('Welcome back!', 'success')
            next_url = safe_next_url(request.args.get('next'), url_for('admin.dashboard'))
            return redirect(next_url)
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout', methods=['GET'])
@login_required
def logout():
    """Admin logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@admin_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Admin dashboard"""
    from app.models.file_share import FileShare
    from app.models.settings import Settings
    
    # Get statistics
    total_shares = FileShare.get_total_count()
    active_shares = FileShare.get_active_count()
    expired_shares = total_shares - active_shares
    
    # Get all settings for display
    all_settings = Settings.get_all()
    
    # Check configuration status
    is_configured = Settings.is_configured()
    needs_setup = Settings.get('needs_initial_setup', False)
    
    # Calculate total storage usage
    total_storage_bytes = 0
    uploads_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    
    if os.path.exists(uploads_dir):
        for root, dirs, files in os.walk(uploads_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_storage_bytes += os.path.getsize(file_path)
                except OSError:
                    pass
    
    stats = {
        'total_shares': total_shares,
        'active_shares': active_shares,
        'expired_shares': expired_shares,
        'is_configured': is_configured,
        'total_storage_bytes': total_storage_bytes,
        'total_storage_gb': total_storage_bytes / (1024**3)
    }
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         settings=all_settings,
                         needs_setup=needs_setup)

@admin_bp.route('/upload', methods=['GET'])
@login_required
def upload():
    """File upload page"""
    app_config = Settings.get_app_config()
    return render_template('admin/upload.html', config=app_config)

@admin_bp.route('/upload/success/<token>', methods=['GET'])
def upload_success(token):
    """Show upload success page"""
    share = FileShare.get(token)
    
    if not share:
        flash(FILE_SHARE_NOT_FOUND, 'error')
        return redirect(url_for('admin.upload'))
        
    total_size_gb = share.get_total_size_gb()
    return render_template('admin/upload_success.html', 
                         share=share, 
                         total_size_gb=total_size_gb)

@admin_bp.route('/api/upload-progress', methods=['GET'])
def upload_progress():
    """API endpoint for upload progress (placeholder for future implementation)"""
    return jsonify({'progress': 0, 'message': 'Upload progress tracking not yet implemented'})

@admin_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    """Settings management page"""
    # Ensure an API key exists to display
    if not Settings.get_api_key():
        Settings.generate_api_key()
    all_settings = Settings.get_all()
    email_config = Settings.get_email_config()
    app_config = Settings.get_app_config()
    timezone_config = Settings.get_timezone_config()
    
    return render_template('admin/settings.html', 
                         settings=all_settings,
                         email_config=email_config,
                         app_config=app_config,
                         timezone_config=timezone_config)

def _update_email_settings(form):
    Settings.set_encrypted('mailjet_api_key', form.get('mailjet_api_key', '').strip(),
                           'Mailjet API Key')
    Settings.set_encrypted('mailjet_api_secret', form.get('mailjet_api_secret', '').strip(),
                           'Mailjet API Secret')
    Settings.set('mailjet_from_email', form.get('mailjet_from_email', '').strip(),
                 'From Email Address')
    Settings.set('mailjet_from_name', form.get('mailjet_from_name', 'Secure File Share').strip(),
                 'From Name')
    flash('Email settings updated successfully!', 'success')


def _update_app_settings(form):
    Settings.set('file_retention_hours', int(form.get('file_retention_hours', 24)),
                 'File retention period in hours')
    Settings.set('max_file_size_gb', int(form.get('max_file_size_gb', 1)),
                 'Maximum file size in GB')
    Settings.set('max_total_upload_gb', int(form.get('max_total_upload_gb', 5)),
                 'Maximum total upload size in GB')
    Settings.set('max_files_per_upload', int(form.get('max_files_per_upload', 10)),
                 'Maximum files per upload')
    Settings.set('require_email', form.get('require_email') == 'on',
                 'Require email for file sharing')
    Settings.set('auto_cleanup', form.get('auto_cleanup') == 'on',
                 'Automatic cleanup of expired files')
    Settings.set('cleanup_interval_minutes', int(form.get('cleanup_interval_minutes', 60)),
                 'Cleanup interval in minutes')
    flash('Application settings updated successfully!', 'success')


def _update_api_settings(form):
    if form.get('regenerate_api_key'):
        Settings.generate_api_key()
        flash('API key regenerated!', 'success')
    Settings.set_notification_email(form.get('notification_email', '').strip())
    flash('API settings updated successfully!', 'success')


def _update_timezone_settings(form):
    timezone = form.get('display_timezone', DEFAULT_TIMEZONE).strip()
    if Settings.set_display_timezone(timezone):
        flash('Timezone settings updated successfully!', 'success')
    else:
        flash('Invalid timezone selected!', 'error')


def _update_admin_credentials(form):
    new_username = form.get('admin_username', '').strip()
    new_password = form.get('admin_password', '').strip()
    confirm_password = form.get('confirm_password', '').strip()

    if new_password and new_password != confirm_password:
        flash('Passwords do not match!', 'error')
        return
    if not new_username:
        return
    try:
        if not new_password:
            Settings.set('admin_username', new_username, 'Admin username')
            flash('Admin username updated successfully!', 'success')
            return
        from app.utils.security import security_manager
        is_secure, issues = security_manager.is_password_secure(new_password)
        if not is_secure:
            flash(f'Password security issues: {", ".join(issues)}', 'error')
            return
        Admin.create_or_update(new_username, new_password)
        flash('Admin credentials updated successfully!', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Error updating admin credentials: {e}', 'error')


_SETTINGS_HANDLERS = (
    ('email_settings', _update_email_settings),
    ('app_settings', _update_app_settings),
    ('api_settings', _update_api_settings),
    ('timezone_settings', _update_timezone_settings),
    ('admin_settings', _update_admin_credentials),
)


@admin_bp.route('/settings', methods=['POST'])
@login_required
def update_settings():
    """Update application settings"""
    try:
        for field, handler in _SETTINGS_HANDLERS:
            if field in request.form:
                handler(request.form)
                break
    except ValueError as e:
        flash(f'Invalid input: {e}', 'error')
    except Exception as e:
        flash(f'Error updating settings: {e}', 'error')
    
    return redirect(url_for('admin.settings'))

@admin_bp.route('/test-email', methods=['POST'])
@login_required
def test_email():
    """Test email configuration"""
    try:
        from app.utils.email import send_test_email
        
        test_email = request.form.get('test_email')
        if not test_email:
            return jsonify({'success': False, 'error': 'Test email address required'})
        
        result = send_test_email(test_email)
        if result:
            return jsonify({'success': True, 'message': 'Test email sent successfully!'})
        else:
            return jsonify({'success': False, 'error': 'Failed to send test email'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/cleanup', methods=['POST'])
@login_required
def manual_cleanup():
    """Manual cleanup of expired files"""
    try:
        from app.utils.cleanup import manual_cleanup
        
        cleaned_count = manual_cleanup()
        return jsonify({
            'success': True, 
            'message': f'Cleanup completed: {cleaned_count} expired shares removed'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/files', methods=['GET'])
@login_required
def files():
    """File management page"""
    page = request.args.get('page', 1, type=int)
    shares = FileShare.get_all_paginated(page=page, per_page=20)
    
    return render_template('admin/files.html', shares=shares)

@admin_bp.route('/files/<token>/delete', methods=['POST'])
@login_required
def delete_file(token):
    """Delete a file share"""
    if FileShare.delete_by_token(token):
        flash('File share deleted successfully!', 'success')
    else:
        flash('Error deleting file share!', 'error')
    
    return redirect(url_for(ADMIN_FILES_ENDPOINT))
    
@admin_bp.route('/files/<token>/notify', methods=['POST'])
@login_required
def notify_share(token):
    """Set recipient (if provided) and send notification email for a share"""
    share = FileShare.get(token)
    if not share:
        flash(FILE_SHARE_NOT_FOUND, 'error')
        return redirect(url_for(ADMIN_FILES_ENDPOINT))
    # If a recipient email was provided, set it and update expiration
    recipient = request.form.get('recipient_email', '').strip()
    if recipient:
        retention = Settings.get('file_retention_hours', 24)
        share.set_recipient(recipient, retention)
    # Send notification
    try:
        from app.utils.email import send_share_notification
        if send_share_notification(share):
            flash('Notification email sent successfully!', 'success')
        else:
            flash('Failed to send notification email.', 'error')
    except Exception:
        current_app.logger.exception("Notification email error")
        flash('Error sending notification email.', 'error')
    return redirect(url_for(ADMIN_FILES_ENDPOINT))

@admin_bp.route('/reactivate/<token>', methods=['POST'])
@login_required
def reactivate_share(token):
    """Reactivate an expired file share"""
    share = FileShare.get(token)

    if not share:
        flash(FILE_SHARE_NOT_FOUND, 'error')
        return redirect(url_for(ADMIN_FILES_ENDPOINT))

    if not share.is_expired():
        flash('File share is already active!', 'info')
        return redirect(url_for(ADMIN_FILES_ENDPOINT))

    # Get retention hours from settings
    from app.models.settings import Settings
    retention_hours = Settings.get('file_retention_hours', 24)
    
    # Reactivate the share with new expiry date
    from datetime import timedelta
    share.expires_at = utc_now() + timedelta(hours=retention_hours)
    share.save()

    flash('File share reactivated successfully!', 'success')
    return redirect(url_for(ADMIN_FILES_ENDPOINT))

def _chunk_error(message, status):
    return jsonify({'success': False, 'error': message}), status


def _parse_chunk_request():
    chunk_number = int(request.form['chunkNumber'])
    total_chunks = int(request.form['totalChunks'])
    file_id = request.form['fileId']
    filename = secure_filename(request.form.get('filename', ''))
    share_token = request.form.get('share_token')

    if not _FILE_ID_RE.fullmatch(file_id or ''):
        return None, _chunk_error('Invalid file id', 400)
    if not filename:
        return None, _chunk_error('Invalid filename', 400)
    if total_chunks < 1 or total_chunks > _MAX_CHUNKS:
        return None, _chunk_error('Invalid chunk count', 400)
    if chunk_number < 1 or chunk_number > total_chunks:
        return None, _chunk_error('Invalid chunk number', 400)

    share = FileShare.get(share_token)
    if not share:
        return None, _chunk_error('Invalid share token', 400)

    return {
        'chunk_number': chunk_number,
        'total_chunks': total_chunks,
        'file_id': file_id,
        'filename': filename,
        'share': share,
    }, None


def _assemble_uploaded_file(temp_dir, total_chunks, filename, share):
    chunk_files = sorted(
        name for name in os.listdir(temp_dir) if _CHUNK_NAME_RE.fullmatch(name)
    )
    if len(chunk_files) != total_chunks:
        return _chunk_error('Missing chunks', 400)

    assembled_path = safe_join_path(temp_dir, 'assembled_file')
    with open(assembled_path, 'wb') as outfile:
        for name in chunk_files:
            with open(safe_join_path(temp_dir, name), 'rb') as infile:
                outfile.write(infile.read())

    uploads_dir = os.path.realpath(current_app.config.get('UPLOAD_FOLDER', 'uploads'))
    upload_dir = safe_join_path(uploads_dir, share.token)
    os.makedirs(upload_dir, exist_ok=True)
    shutil.move(assembled_path, safe_join_path(upload_dir, filename))

    if not share.files:
        share.files = []
    if filename not in share.files:
        share.files.append(filename)
    share.save()

    for name in chunk_files:
        try:
            os.remove(safe_join_path(temp_dir, name))
        except OSError:
            pass
    try:
        os.rmdir(temp_dir)
    except OSError:
        pass
    return None


@admin_bp.route('/upload-chunk', methods=['POST'])
@login_required
def upload_chunk():
    """Handle chunked file upload via AJAX"""
    try:
        parsed, error = _parse_chunk_request()
        if error:
            return error

        chunks_root = os.path.realpath(os.path.join(tempfile.gettempdir(), 'chunked_uploads'))
        os.makedirs(chunks_root, exist_ok=True)
        temp_dir = safe_join_path(chunks_root, parsed['file_id'])
        os.makedirs(temp_dir, exist_ok=True)

        chunk_name = f"chunk_{parsed['chunk_number']:05d}"
        request.files['chunk'].save(safe_join_path(temp_dir, chunk_name))

        if parsed['chunk_number'] != parsed['total_chunks']:
            return jsonify({'success': True, 'done': False}), 200

        assemble_error = _assemble_uploaded_file(
            temp_dir, parsed['total_chunks'], parsed['filename'], parsed['share']
        )
        if assemble_error:
            return assemble_error
        return jsonify({'success': True, 'done': True, 'token': parsed['share'].token}), 200
    except ValueError:
        current_app.logger.exception("Chunk upload path error")
        return jsonify({'success': False, 'error': 'Invalid upload path'}), 400
    except Exception as e:
        current_app.logger.exception("Chunk upload error")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/request-share-token', methods=['POST'])
@login_required
def request_share_token():
    data = request.get_json()
    recipient_email = data.get('recipient_email', '').strip()
    retention_hours = int(data.get('retention_hours', 24))
    # Create a new share and return the token
    share = FileShare.create(recipient_email, [], retention_hours)
    return jsonify({'token': share.token})

@admin_bp.route('/finalize-share', methods=['POST'])
@login_required
def finalize_share():
    """Send email notification after all chunked uploads are complete"""
    data = request.get_json()
    share_token = data.get('share_token')
    share = FileShare.get(share_token)
    if not share:
        return jsonify({'success': False, 'error': 'Invalid share token'}), 400
    try:
        email_config = Settings.get_email_config()
        api_key = email_config['api_key']
        api_secret = email_config['api_secret']
        if api_key and api_secret:
            from app.utils.email import send_share_notification
            send_share_notification(share)
        return jsonify({'success': True}), 200
    except Exception as e:
        current_app.logger.exception("Email error (finalize)")
        return jsonify({'success': False, 'error': str(e)}), 500
