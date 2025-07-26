import os
import json
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class FileShare:
    def __init__(self, token: str, recipient_email: str, files: List[str], 
                 created_at: datetime, expires_at: datetime, downloaded: bool = False,
                 download_count: int = 0, downloaded_files: Optional[List[str]] = None):
        self.token = token
        self.recipient_email = recipient_email
        self.files = files
        self.created_at = created_at
        self.expires_at = expires_at
        self.downloaded = downloaded
        self.download_count = download_count
        self.downloaded_files = downloaded_files if downloaded_files is not None else []

    @staticmethod
    def get_uploads_dir():
        """Get the uploads directory path"""
        try:
            from flask import current_app
            return current_app.config.get('UPLOAD_FOLDER', 'uploads')
        except:
            return 'uploads'
    
    @staticmethod
    def init_db():
        """Initialize file_shares table"""
        from app.utils.database import get_db_connection
        conn = get_db_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS file_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                recipient_email TEXT NOT NULL,
                files TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                downloaded BOOLEAN DEFAULT 0,
                download_count INTEGER DEFAULT 0,
                downloaded_files TEXT DEFAULT '[]',
                last_download_attempt TIMESTAMP,
                last_download_completed TIMESTAMP,
                bytes_transferred INTEGER
            )
        ''')
        conn.commit()
        conn.close()
    
    @staticmethod
    def upgrade_db_schema():
        """Add new columns for enhanced download tracking"""
        from app.utils.database import get_db_connection
        
        conn = get_db_connection()
        
        # Add new columns if they don't exist
        new_columns = [
            ('last_download_attempt', 'TIMESTAMP'),
            ('last_download_completed', 'TIMESTAMP'), 
            ('bytes_transferred', 'INTEGER'),
            ('downloaded_files', 'TEXT DEFAULT "[]"')
        ]
        
        for column_name, column_type in new_columns:
            try:
                conn.execute(f'ALTER TABLE file_shares ADD COLUMN {column_name} {column_type}')
            except Exception:
                # Column already exists
                pass
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def generate_token() -> str:
        """Generate a cryptographically secure token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create(recipient_email: str, files: List[str], retention_hours: int = 24) -> 'FileShare':
        """Create a new file share"""
        from app.utils.database import get_db_connection
        
        token = FileShare.generate_token()
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=retention_hours)
        
        # Save to database
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO file_shares (token, recipient_email, files, created_at, expires_at, downloaded_files)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (token, recipient_email, json.dumps(files), created_at, expires_at, json.dumps([])))
        conn.commit()
        
        # Verify the data was saved correctly
        cursor = conn.execute('SELECT created_at, expires_at FROM file_shares WHERE token = ?', (token,))
        row = cursor.fetchone()
        if row:
            created_at = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
            expires_at = datetime.fromisoformat(row[1].replace('Z', '+00:00'))
            
        conn.close()
        
        # Create instance with verified datetime objects
        share = FileShare(token, recipient_email, files, created_at, expires_at)
        return share
    
    def save(self):
        """Save file share metadata to database"""
        from app.utils.database import get_db_connection
        
        conn = get_db_connection()
        conn.execute('''
            UPDATE file_shares 
            SET files = ?, downloaded = ?, download_count = ?, expires_at = ?, downloaded_files = ?
            WHERE token = ?
        ''', (json.dumps(self.files), self.downloaded, self.download_count, self.expires_at, json.dumps(self.downloaded_files), self.token))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get(token: str) -> Optional['FileShare']:
        """Get file share by token"""
        from app.utils.database import get_db_connection
        
        try:
            conn = get_db_connection()
            cursor = conn.execute('''
                SELECT token, recipient_email, files, created_at, expires_at, downloaded, download_count, downloaded_files
                FROM file_shares WHERE token = ?
            ''', (token,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                token, recipient_email, files_json, created_at_str, expires_at_str, downloaded, download_count, downloaded_files_json = row
                
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                files = json.loads(files_json)
                downloaded_files = json.loads(downloaded_files_json) if downloaded_files_json else []
                
                return FileShare(token, recipient_email, files, created_at, expires_at, bool(downloaded), download_count, downloaded_files)
            
            return None
            
        except Exception as e:
            print(f"Error getting file share {token}: {e}")
            return None
    
    @staticmethod
    def get_all_active() -> List['FileShare']:
        """Get all active file shares, including downloaded_files"""
        from app.utils.database import get_db_connection
        shares = []
        try:
            conn = get_db_connection()
            cursor = conn.execute('''
                SELECT token, recipient_email, files, created_at, expires_at, downloaded, download_count, downloaded_files
                FROM file_shares 
                WHERE datetime(expires_at) > datetime('now')
                ORDER BY created_at DESC
            ''')
            for row in cursor.fetchall():
                token, recipient_email, files_json, created_at_str, expires_at_str, downloaded, download_count, downloaded_files_json = row
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                files = json.loads(files_json)
                downloaded_files = json.loads(downloaded_files_json) if downloaded_files_json else []
                shares.append(FileShare(token, recipient_email, files, created_at, expires_at, bool(downloaded), download_count, downloaded_files))
            conn.close()
        except Exception as e:
            print(f"Error getting active shares: {e}")
        return shares
    
    @staticmethod
    def get_all_paginated(page: int = 1, per_page: int = 20):
        """Get paginated file shares, including downloaded_files"""
        from app.utils.database import get_db_connection
        try:
            conn = get_db_connection()
            offset = (page - 1) * per_page
            cursor = conn.execute('''
                SELECT token, recipient_email, files, created_at, expires_at, downloaded, download_count, downloaded_files
                FROM file_shares 
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
            shares = []
            for row in cursor.fetchall():
                token, recipient_email, files_json, created_at_str, expires_at_str, downloaded, download_count, downloaded_files_json = row
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                files = json.loads(files_json)
                downloaded_files = json.loads(downloaded_files_json) if downloaded_files_json else []
                shares.append(FileShare(token, recipient_email, files, created_at, expires_at, bool(downloaded), download_count, downloaded_files))
            # Get total count for pagination
            cursor = conn.execute('SELECT COUNT(*) FROM file_shares')
            total = cursor.fetchone()[0]
            conn.close()
            # Create pagination object
            class Pagination:
                def __init__(self, page, per_page, total, items):
                    self.page = page
                    self.per_page = per_page
                    self.total = total
                    self.items = items
                    self.pages = (total + per_page - 1) // per_page
                    self.has_prev = page > 1
                    self.has_next = page < self.pages
                    self.prev_num = page - 1 if self.has_prev else None
                    self.next_num = page + 1 if self.has_next else None
            return Pagination(page, per_page, total, shares)
        except Exception as e:
            print(f"Error getting paginated shares: {e}")
            return Pagination(1, per_page, 0, [])
    
    @staticmethod
    def get_total_count() -> int:
        """Get total number of file shares"""
        from app.utils.database import get_db_connection
        
        try:
            conn = get_db_connection()
            cursor = conn.execute('SELECT COUNT(*) FROM file_shares')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    @staticmethod
    def get_active_count() -> int:
        """Get number of active file shares"""
        from app.utils.database import get_db_connection
        
        try:
            conn = get_db_connection()
            cursor = conn.execute('''
                SELECT COUNT(*) FROM file_shares 
                WHERE datetime(expires_at) > datetime('now')
            ''')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    @staticmethod
    def get_expired_shares():
        """Get all expired file shares"""
        from app.utils.database import get_db_connection
        import json
        
        try:
            conn = get_db_connection()
            cursor = conn.execute('''
                SELECT token, recipient_email, files, created_at, expires_at, downloaded, download_count
                FROM file_shares 
                WHERE datetime(expires_at) <= datetime('now')
                AND recipient_email IS NOT NULL AND recipient_email != ''
            ''')
            
            expired_shares = []
            for row in cursor.fetchall():
                token, recipient_email, files_json, created_at_str, expires_at_str, downloaded, download_count = row
                
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                files = json.loads(files_json)
                
                expired_shares.append(FileShare(token, recipient_email, files, created_at, expires_at, bool(downloaded), download_count))
            
            conn.close()
            return expired_shares
            
        except Exception as e:
            print(f"Error getting expired shares: {e}")
            return []

    @staticmethod
    def delete_by_token(token: str) -> bool:
        """Delete file share by token"""
        from app.utils.database import get_db_connection
        import shutil
        
        try:
            # Delete physical files
            uploads_dir = FileShare.get_uploads_dir()
            share_dir = os.path.join(uploads_dir, token)
            if os.path.exists(share_dir):
                shutil.rmtree(share_dir)
            
            # Delete database record
            conn = get_db_connection()
            conn.execute('DELETE FROM file_shares WHERE token = ?', (token,))
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"Error deleting file share {token}: {e}")
            return False
    
    def is_expired(self) -> bool:
        """Check if the file share has expired. Shares without recipient never expire."""
        # Never expire if no recipient assigned
        if not self.recipient_email:
            return False
        # If expires_at missing, treat as not expired
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def mark_downloaded(self):
        """Mark as downloaded and increment count"""
        from app.utils.database import get_db_connection
        
        self.downloaded = True
        self.download_count += 1
        
        try:
            conn = get_db_connection()
            conn.execute('''
                UPDATE file_shares 
                SET downloaded = ?, download_count = ?, last_download_completed = ?, downloaded_files = ?
                WHERE token = ?
            ''', (self.downloaded, self.download_count, datetime.utcnow(), json.dumps(self.downloaded_files), self.token))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error marking downloaded {self.token}: {e}")

    def mark_file_downloaded(self, filename: str):
        """Mark a specific file as downloaded"""
        if filename not in self.downloaded_files:
            self.downloaded_files.append(filename)
            self.save()
    
    def mark_download_attempt(self):
        """Mark download attempt"""
        from app.utils.database import get_db_connection
        
        try:
            conn = get_db_connection()
            conn.execute('''
                UPDATE file_shares 
                SET last_download_attempt = ?
                WHERE token = ?
            ''', (datetime.utcnow(), self.token))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error marking download attempt {self.token}: {e}")
    
    def get_file_path(self, filename: str) -> str:
        """Get full path to a file in this share"""
        uploads_dir = self.get_uploads_dir()
        return os.path.join(uploads_dir, self.token, filename)
    
    def set_recipient(self, recipient_email: str, retention_hours: int) -> None:
        """
        Assign recipient and update expiration based on retention hours.
        """
        from app.utils.database import get_db_connection
        # Set in-memory
        self.recipient_email = recipient_email
        self.expires_at = datetime.utcnow() + timedelta(hours=retention_hours)
        # Persist to DB
        conn = get_db_connection()
        conn.execute(
            'UPDATE file_shares SET recipient_email = ?, expires_at = ? WHERE token = ?',
            (recipient_email, self.expires_at, self.token)
        )
        conn.commit()
        conn.close()
    
    def get_total_size_bytes(self) -> int:
        """Get total size of all files in bytes"""
        total_size = 0
        uploads_dir = self.get_uploads_dir()
        share_dir = os.path.join(uploads_dir, self.token)
        
        if os.path.exists(share_dir):
            for filename in self.files:
                file_path = os.path.join(share_dir, filename)
                if os.path.exists(file_path):
                    try:
                        total_size += os.path.getsize(file_path)
                    except:
                        pass
        
        return total_size
    
    def get_total_size_gb(self) -> float:
        """Get total size of all files in GB"""
        bytes_size = self.get_total_size_bytes()
        return bytes_size / (1024 ** 3)
    
    def delete(self):
        """Delete the file share and all associated files"""
        FileShare.delete_by_token(self.token)
    
    @staticmethod
    def cleanup_expired_files():
        """Clean up expired file shares if auto cleanup is enabled"""
        from app.models.settings import Settings
        from app.utils.database import get_db_connection
        import shutil
        
        # Check if auto cleanup is enabled
        if not Settings.get('auto_cleanup', True):
            return 0
        
        try:
            conn = get_db_connection()
            
            # Get expired file shares
            cursor = conn.execute('''
                SELECT token FROM file_shares
                WHERE datetime(expires_at) < datetime('now')
            ''')
            
            expired_tokens = [row[0] for row in cursor.fetchall()]
            deleted_count = 0
            uploads_dir = FileShare.get_uploads_dir()
            
            for token in expired_tokens:
                try:
                    # Delete physical files
                    share_dir = os.path.join(uploads_dir, token)
                    if os.path.exists(share_dir):
                        shutil.rmtree(share_dir)
                    
                    # Delete database record
                    conn.execute('DELETE FROM file_shares WHERE token = ?', (token,))
                    deleted_count += 1
                    
                except Exception as e:
                    print(f"Error cleaning up {token}: {e}")
            
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                print(f"✅ Cleaned up {deleted_count} expired file shares")
            
            return deleted_count
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
            return 0
    
    def get_created_at_user_timezone(self, format_str='%d/%m/%Y %H:%M %Z') -> str:
        """Get created_at formatted in user's configured timezone"""
        from app.utils.helpers import format_datetime_user_timezone
        return format_datetime_user_timezone(self.created_at, format_str)
    
    def get_expires_at_user_timezone(self, format_str='%d/%m/%Y %H:%M %Z') -> str:
        """Get expires_at formatted in user's configured timezone"""
        from app.utils.helpers import format_datetime_user_timezone
        return format_datetime_user_timezone(self.expires_at, format_str)
    
    def get_created_date_user_timezone(self) -> str:
        """Get created date only in user's configured timezone"""
        from app.utils.helpers import format_date_user_timezone
        return format_date_user_timezone(self.created_at)
    
    def get_expires_date_user_timezone(self) -> str:
        """Get expires date only in user's configured timezone"""
        from app.utils.helpers import format_date_user_timezone
        return format_date_user_timezone(self.expires_at)

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            'token': self.token,
            'recipient_email': self.recipient_email,
            'files': self.files,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'created_at_user_tz': self.get_created_at_user_timezone(),
            'expires_at_user_tz': self.get_expires_at_user_timezone(),
            'created_date_user_tz': self.get_created_date_user_timezone(),
            'expires_date_user_tz': self.get_expires_date_user_timezone(),
            'downloaded': self.downloaded,
            'download_count': self.download_count,
            'is_expired': self.is_expired(),
            'total_size_bytes': self.get_total_size_bytes(),
            'total_size_gb': self.get_total_size_gb()
        }
