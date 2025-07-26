import os
import shutil
from werkzeug.utils import secure_filename
from typing import List
from flask import current_app

def save_uploaded_files(files, token: str) -> List[str]:
    """Save uploaded files to token directory"""
    token_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], token)
    os.makedirs(token_dir, exist_ok=True)
    
    saved_files = []
    
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            if filename:  # Ensure filename is not empty after securing
                file_path = os.path.join(token_dir, filename)
                
                # Handle duplicate filenames
                counter = 1
                original_filename = filename
                while os.path.exists(file_path):
                    name, ext = os.path.splitext(original_filename)
                    filename = f"{name}_{counter}{ext}"
                    file_path = os.path.join(token_dir, filename)
                    counter += 1
                
                file.save(file_path)
                saved_files.append(filename)
    
    return saved_files

def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

# def format_file_size(size_bytes: int) -> str:
#     """Format file size in human readable format"""
#     if size_bytes == 0:
#         return "0 B"
    
#     size_names = ["B", "KB", "MB", "GB", "TB"]
#     i = 0
#     while size_bytes >= 1024 and i < len(size_names) - 1:
#         size_bytes /= 1024.0
#         i += 1
    
#     return f"{size_bytes:.1f} {size_names[i]}"
