import hashlib
from typing import Optional
from flask_login import UserMixin
from app.utils.database import get_db_connection
from app.utils.security import security_manager

class Admin(UserMixin):
    def __init__(self, username: str, password_hash: str):
        self.id = username  # Flask-Login requires an 'id' attribute
        self.username = username
        self.password_hash = password_hash
    
    @staticmethod
    def create_or_update(username: str, password: str) -> 'Admin':
        """Create or update an admin user with secure password hashing"""
        # Check password security
        is_secure, issues = security_manager.is_password_secure(password)
        if not is_secure:
            raise ValueError(f"Password security issues: {', '.join(issues)}")
        
        # Hash password securely using bcrypt
        password_hash = security_manager.hash_password(password)
        
        conn = get_db_connection()
        
        # Check if this is an update of an existing user with old SHA256 hash
        cursor = conn.execute('SELECT password_hash FROM admin_users WHERE username = ?', (username,))
        existing_row = cursor.fetchone()
        
        if existing_row and len(existing_row['password_hash']) == 64:
            # This is an old SHA256 hash, log the upgrade
            print(f"INFO: Upgrading admin user '{username}' from SHA256 to bcrypt")
        
        conn.execute('''
            INSERT OR REPLACE INTO admin_users (username, password_hash, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (username, password_hash))
        conn.commit()
        conn.close()
        
        return Admin(username, password_hash)
    
    @staticmethod
    def get(username: str) -> Optional['Admin']:
        """Get admin user by username"""
        conn = get_db_connection()
        cursor = conn.execute('SELECT username, password_hash FROM admin_users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Admin(row['username'], row['password_hash'])
        return None
    
    @staticmethod
    def exists() -> bool:
        """Check if any admin users exist"""
        conn = get_db_connection()
        cursor = conn.execute('SELECT COUNT(*) as count FROM admin_users')
        count = cursor.fetchone()['count']
        conn.close()
        return count > 0
    
    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash with support for legacy SHA256 migration"""
        # Check if this is a new bcrypt hash
        if self.password_hash.startswith('$2b$') or self.password_hash.startswith('$2a$') or self.password_hash.startswith('$2y$'):
            return security_manager.verify_password(password, self.password_hash)
        
        # Legacy SHA256 hash - verify and upgrade if correct
        elif len(self.password_hash) == 64:  # SHA256 hex length
            legacy_hash = hashlib.sha256(password.encode()).hexdigest()
            if self.password_hash == legacy_hash:
                # Password is correct, upgrade to bcrypt
                print(f"INFO: Migrating admin user '{self.username}' from SHA256 to bcrypt")
                try:
                    new_hash = security_manager.hash_password(password)
                    conn = get_db_connection()
                    conn.execute('''
                        UPDATE admin_users 
                        SET password_hash = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE username = ?
                    ''', (new_hash, self.username))
                    conn.commit()
                    conn.close()
                    
                    # Update current instance
                    self.password_hash = new_hash
                    print(f"INFO: Successfully upgraded admin user '{self.username}' to bcrypt")
                    return True
                except Exception as e:
                    print(f"ERROR: Failed to upgrade admin user '{self.username}': {e}")
                    return True  # Still allow login even if upgrade fails
            return False
        
        # Unknown hash format
        else:
            print(f"WARNING: Unknown password hash format for admin user '{self.username}'")
            return False
    
    def get_id(self):
        """Required by Flask-Login"""
        return self.username

    @staticmethod
    def authenticate(username: str, password: str) -> Optional['Admin']:
        """Authenticate admin user with username and password"""
        admin = Admin.get(username)
        if admin and admin.verify_password(password):
            return admin
        return None
