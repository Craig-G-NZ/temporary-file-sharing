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
        """Verify password against stored bcrypt hash"""
        if self.password_hash.startswith(('$2b$', '$2a$', '$2y$')):
            return security_manager.verify_password(password, self.password_hash)

        print(
            f"WARNING: Admin user '{self.username}' has a non-bcrypt password hash; "
            "reset the password via Admin.create_or_update or ADMIN_PASSWORD"
        )
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
