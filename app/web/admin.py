from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.utils import secure_filename
from app.models.admin import Admin
from app.models.settings import Settings
from app.models.file_share import FileShare
from app.utils.helpers import format_file_size
import os
import tempfile

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

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
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
@login_required
def logout():
    """Admin logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@admin_bp.route('/dashboard')
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
                except:
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

@admin_bp.route('/upload')
@login_required
def upload():
    """File upload page"""
    app_config = Settings.get_app_config()
    return render_template('admin/upload.html', config=app_config)

@admin_bp.route('/upload/success/<token>')
def upload_success(token):
    """Show upload success page"""
    share = FileShare.get(token)
    
    if not share:
        flash('File share not found!', 'error')
        return redirect(url_for('admin.upload'))
        
    total_size_gb = share.get_total_size_gb()
    return render_template('admin/upload_success.html', 
                         share=share, 
                         total_size_gb=total_size_gb)

@admin_bp.route('/api/upload-progress')
def upload_progress():
    """API endpoint for upload progress (placeholder for future implementation)"""
    return jsonify({'progress': 0, 'message': 'Upload progress tracking not yet implemented'})

@admin_bp.route('/settings')
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

@admin_bp.route('/settings', methods=['POST'])
@login_required
def update_settings():
    """Update application settings"""
    try:
        # Email settings
        if 'email_settings' in request.form:
            Settings.set_encrypted('mailjet_api_key', request.form.get('mailjet_api_key', '').strip(),
                        'Mailjet API Key')
            Settings.set_encrypted('mailjet_api_secret', request.form.get('mailjet_api_secret', '').strip(),
                        'Mailjet API Secret')
            Settings.set('mailjet_from_email', request.form.get('mailjet_from_email', '').strip(),
                        'From Email Address')
            Settings.set('mailjet_from_name', request.form.get('mailjet_from_name', 'Secure File Share').strip(),
                        'From Name')
            flash('Email settings updated successfully!', 'success')
        
        # App settings
        elif 'app_settings' in request.form:
            Settings.set('file_retention_hours', int(request.form.get('file_retention_hours', 24)),
                        'File retention period in hours')
            Settings.set('max_file_size_gb', int(request.form.get('max_file_size_gb', 1)),
                        'Maximum file size in GB')
            Settings.set('max_total_upload_gb', int(request.form.get('max_total_upload_gb', 5)),
                        'Maximum total upload size in GB')
            Settings.set('max_files_per_upload', int(request.form.get('max_files_per_upload', 10)),
                        'Maximum files per upload')
            Settings.set('require_email', request.form.get('require_email') == 'on',
                        'Require email for file sharing')
            Settings.set('auto_cleanup', request.form.get('auto_cleanup') == 'on',
                        'Automatic cleanup of expired files')
            Settings.set('cleanup_interval_minutes', int(request.form.get('cleanup_interval_minutes', 60)),
                        'Cleanup interval in minutes')
            flash('Application settings updated successfully!', 'success')
        
        # API settings
        elif 'api_settings' in request.form:
            # Regenerate API key if requested
            if request.form.get('regenerate_api_key'):
                new_key = Settings.generate_api_key()
                flash('API key regenerated!', 'success')
            # Update notification email
            notif_email = request.form.get('notification_email', '').strip()
            Settings.set_notification_email(notif_email)
            flash('API settings updated successfully!', 'success')
        
        # Timezone settings
        elif 'timezone_settings' in request.form:
            timezone = request.form.get('display_timezone', 'Pacific/Auckland').strip()
            if Settings.set_display_timezone(timezone):
                flash('Timezone settings updated successfully!', 'success')
            else:
                flash('Invalid timezone selected!', 'error')
                
        # Admin settings
        elif 'admin_settings' in request.form:
            new_username = request.form.get('admin_username', '').strip()
            new_password = request.form.get('admin_password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            
            if new_password and new_password != confirm_password:
                flash('Passwords do not match!', 'error')
            elif new_username:
                try:
                    if new_password:
                        # Validate password security
                        from app.utils.security import security_manager
                        is_secure, issues = security_manager.is_password_secure(new_password)
                        if not is_secure:
                            flash(f'Password security issues: {", ".join(issues)}', 'error')
                        else:
                            Admin.create_or_update(new_username, new_password)
                            flash('Admin credentials updated successfully!', 'success')
                    else:
                        # Just update username (not recommended, but supported)
                        Settings.set('admin_username', new_username, 'Admin username')
                        flash('Admin username updated successfully!', 'success')
                except ValueError as e:
                    flash(str(e), 'error')
                except Exception as e:
                    flash(f'Error updating admin credentials: {e}', 'error')
        
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

@admin_bp.route('/files')
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
    
    return redirect(url_for('admin.files'))
    
@admin_bp.route('/files/<token>/notify', methods=['POST'])
@login_required
def notify_share(token):
    """Set recipient (if provided) and send notification email for a share"""
    share = FileShare.get(token)
    if not share:
        flash('File share not found!', 'error')
        return redirect(url_for('admin.files'))
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
    except Exception as e:
        current_app.logger.error(f"Notification email error: {e}")
        flash('Error sending notification email.', 'error')
    return redirect(url_for('admin.files'))

@admin_bp.route('/reactivate/<token>', methods=['POST'])
@login_required
def reactivate_share(token):
    """Reactivate an expired file share"""
    share = FileShare.get(token)

    if not share:
        flash('File share not found!', 'error')
        return redirect(url_for('admin.files'))

    if not share.is_expired():
        flash('File share is already active!', 'info')
        return redirect(url_for('admin.files'))

    # Get retention hours from settings
    from app.models.settings import Settings
    retention_hours = Settings.get('file_retention_hours', 24)
    
    # Reactivate the share with new expiry date
    from datetime import datetime, timedelta
    share.expires_at = datetime.utcnow() + timedelta(hours=retention_hours)
    share.save()

    flash('File share reactivated successfully!', 'success')
    return redirect(url_for('admin.files'))

@admin_bp.route('/upload-chunk', methods=['POST'])
@login_required
def upload_chunk():
    """Handle chunked file upload via AJAX"""
    try:
        chunk_number = int(request.form['chunkNumber'])
        total_chunks = int(request.form['totalChunks'])
        file_id = request.form['fileId']
        filename = secure_filename(request.form['filename'])
        share_token = request.form.get('share_token')
        # Get the share by token
        share = FileShare.get(share_token)
        if not share:
            return jsonify({'success': False, 'error': 'Invalid share token'}), 400

        # Chunk data
        chunk = request.files['chunk']

        # Temp dir for chunks
        temp_dir = os.path.join(tempfile.gettempdir(), 'chunked_uploads', file_id)
        os.makedirs(temp_dir, exist_ok=True)
        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_number:05d}")
        chunk.save(chunk_path)

        # If last chunk, assemble file
        if chunk_number == total_chunks:
            # Assemble chunks
            assembled_path = os.path.join(temp_dir, filename)
            with open(assembled_path, 'wb') as outfile:
                for i in range(1, total_chunks + 1):
                    part_path = os.path.join(temp_dir, f"chunk_{i:05d}")
                    with open(part_path, 'rb') as infile:
                        outfile.write(infile.read())

            # Save to uploads dir under the existing share
            uploads_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            upload_dir = os.path.join(uploads_dir, share.token)
            os.makedirs(upload_dir, exist_ok=True)
            final_path = os.path.join(upload_dir, filename)
            import shutil
            shutil.move(assembled_path, final_path)
            
            # Add file to share.files (append if not already present)
            if not share.files:
                share.files = []
            if filename not in share.files:
                share.files.append(filename)
            share.save()

            # Cleanup temp chunks
            for i in range(1, total_chunks + 1):
                try:
                    os.remove(os.path.join(temp_dir, f"chunk_{i:05d}"))
                except Exception:
                    pass
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass

            return jsonify({'success': True, 'done': True, 'token': share.token}), 200
        else:
            return jsonify({'success': True, 'done': False}), 200
    except Exception as e:
        current_app.logger.error(f"Chunk upload error: {e}")
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
        current_app.logger.error(f"Email error (finalize): {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
