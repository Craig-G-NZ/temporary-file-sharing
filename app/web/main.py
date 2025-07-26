from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file, abort
from flask_login import login_required
from werkzeug.utils import secure_filename
from app.models.settings import Settings
from app.models.file_share import FileShare
from app.utils.helpers import format_file_size, validate_file_size, gb_to_bytes
import os
import zipfile
import tempfile
import pytz
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page"""
    app_config = Settings.get_app_config()
    is_configured = Settings.is_configured()
    
    return render_template('main/index.html', 
                         config=app_config, 
                         is_configured=is_configured)

@main_bp.route('/download/<token>')
def download_page(token):
    """Download page for a file share"""
    share = FileShare.get(token)
    
    if not share:
        flash('File share not found!', 'error')
        return render_template('errors/404.html'), 404
    
    if share.is_expired():
        flash('File share has expired!', 'error')
        return render_template('errors/expired.html'), 410
    
    # Mark download attempt
    share.mark_download_attempt()
    
    # Get file info with sizes
    file_info = []
    total_size_bytes = 0
    for filename in share.files:
        file_path = share.get_file_path(filename)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            file_info.append({
                'name': filename,
                'size_bytes': file_size,
                'size_formatted': format_file_size(file_size),
                'size_gb': file_size / (1024**3)
            })
            total_size_bytes += file_size
    # Attach file info to share object for template
    share.file_info = file_info
    share.total_size_bytes = total_size_bytes
    share.total_size_gb = total_size_bytes / (1024**3)
    share.total_size_formatted = format_file_size(total_size_bytes)
    # Initialize timezone and utilities for template
    nz_tz = pytz.timezone('Pacific/Auckland')
    return render_template('main/download.html', 
                         share=share, 
                         pytz=pytz, 
                         nz_tz=nz_tz,
                         hasattr=hasattr)

@main_bp.route('/download/<token>/file/<filename>')
def download_file(token, filename):
    """Download individual file"""
    share = FileShare.get(token)
    
    if not share:
        abort(404)
    
    if share.is_expired():
        abort(410)
    
    # Security check
    if filename not in share.files:
        abort(404)
    
    file_path = share.get_file_path(filename)
    
    if not os.path.exists(file_path):
        abort(404)
    
    # Mark as downloaded
    share.mark_file_downloaded(filename)
    share.mark_downloaded()
    
    # Log download
    file_size = os.path.getsize(file_path)
    current_app.logger.info(f"📥 Download: {filename} ({format_file_size(file_size)}) - Token: {token}")
    
    return send_file(file_path, as_attachment=True, download_name=filename)

@main_bp.route('/download/<token>/zip')
def download_zip(token):
    """Download all files as ZIP"""
    share = FileShare.get(token)
    
    if not share:
        abort(404)
    
    if share.is_expired():
        abort(410)
    
    # Create temporary ZIP file
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            total_size = 0
            
            for filename in share.files:
                file_path = share.get_file_path(filename)
                if os.path.exists(file_path):
                    zip_file.write(file_path, filename)
                    total_size += os.path.getsize(file_path)
        
        # Mark as downloaded
        share.mark_downloaded()
        
        # Log download
        current_app.logger.info(f"📦 ZIP Download: {len(share.files)} files ({format_file_size(total_size)}) - Token: {token}")
        
        zip_filename = f"files_{token[:8]}.zip"
        return send_file(temp_zip.name, as_attachment=True, download_name=zip_filename)
        
    except Exception as e:
        current_app.logger.error(f"ZIP creation error: {e}")
        abort(500)
    finally:
        # Clean up temp file after sending
        try:
            os.unlink(temp_zip.name)
        except:
            pass

