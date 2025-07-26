import os
import shutil
import threading
import time
from datetime import datetime
from app.models.file_share import FileShare
from flask import current_app

class CleanupScheduler:
    """Background scheduler for cleaning up expired files"""
    
    def __init__(self, app=None):
        self.app = app
        self.running = False
        self.thread = None
        
    def init_app(self, app):
        """Initialize the scheduler with Flask app"""
        self.app = app
        
    def start(self):
        """Start the cleanup scheduler"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        current_app.logger.info("Cleanup scheduler started")
        
    def stop(self):
        """Stop the cleanup scheduler"""
        self.running = False
        if self.thread:
            self.thread.join()
        current_app.logger.info("Cleanup scheduler stopped")
            
    def _run_scheduler(self):
        """Main scheduler loop"""
        with self.app.app_context():
            while self.running:
                try:
                    # Check if auto cleanup is enabled  
                    from app.models.settings import Settings
                    if Settings.get('auto_cleanup', True):
                        cleaned_count = cleanup_expired_files()
                        if cleaned_count > 0:
                            current_app.logger.info(f"Automated cleanup: {cleaned_count} expired shares removed")
                    
                    # Get cleanup interval in minutes (default 60 minutes)
                    interval_minutes = Settings.get('cleanup_interval_minutes', 60)
                    time.sleep(interval_minutes * 60)  # Convert to seconds
                    
                except Exception as e:
                    current_app.logger.error(f"Cleanup scheduler error: {e}")
                    time.sleep(300)  # Wait 5 minutes before retrying on error

def cleanup_expired_files() -> int:
    """Clean up expired file shares"""
    cleaned_count = 0
    uploads_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    
    if not os.path.exists(uploads_dir):
        return cleaned_count
    
    for token_dir in os.listdir(uploads_dir):
        token_path = os.path.join(uploads_dir, token_dir)
        
        if not os.path.isdir(token_path):
            continue
        
        file_share = FileShare.get(token_dir)
        
        if file_share and file_share.is_expired():
            try:
                shutil.rmtree(token_path)
                cleaned_count += 1
                current_app.logger.info(f"Cleaned up expired share: {token_dir}")
            except Exception as e:
                current_app.logger.error(f"Failed to clean up {token_dir}: {e}")
        elif not file_share:
            # Clean up orphaned directories without metadata
            try:
                shutil.rmtree(token_path)
                cleaned_count += 1
                current_app.logger.info(f"Cleaned up orphaned directory: {token_dir}")
            except Exception as e:
                current_app.logger.error(f"Failed to clean up orphaned {token_dir}: {e}")
    
    return cleaned_count

def cleanup_orphaned_directories(uploads_dir: str) -> int:
    """Clean up directories that don't have corresponding database entries"""
    cleaned_count = 0
    
    try:
        for item in os.listdir(uploads_dir):
            item_path = os.path.join(uploads_dir, item)
            
            if not os.path.isdir(item_path):
                continue
                
            # Check if this token exists in database
            share = FileShare.get(item)
            if not share:
                try:
                    shutil.rmtree(item_path)
                    cleaned_count += 1
                    current_app.logger.info(f"Cleaned up orphaned directory: {item}")
                except Exception as e:
                    current_app.logger.error(f"Failed to clean up orphaned directory {item}: {e}")
                    
    except Exception as e:
        current_app.logger.error(f"Orphaned directory cleanup failed: {e}")
    
    return cleaned_count

def manual_cleanup() -> int:
    """Manual cleanup function for admin use"""
    return cleanup_expired_files()

def schedule_cleanup():
    """Legacy function for backward compatibility - now redirects to manual cleanup"""
    return manual_cleanup()

# Global scheduler instance
cleanup_scheduler = CleanupScheduler()
