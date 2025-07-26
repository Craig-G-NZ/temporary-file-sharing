"""
Security utilities for encrypting sensitive data and hashing passwords
"""
import bcrypt
import secrets
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
from typing import Optional

class SecurityManager:
    """Handles secure password hashing and sensitive data encryption"""
    
    def __init__(self):
        self._encryption_key = None
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt with a random salt
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Bcrypt hashed password string
        """
        # Generate a salt and hash the password
        salt = bcrypt.gensalt(rounds=12)  # 12 rounds is a good balance of security vs performance
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        return password_hash.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            password: Plain text password to verify
            hashed_password: Previously hashed password to check against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except (ValueError, TypeError):
            return False
    
    def get_encryption_key(self) -> bytes:
        """
        Get or generate the encryption key for sensitive data
        
        Returns:
            Fernet encryption key
        """
        if self._encryption_key is not None:
            return self._encryption_key
            
        # Try to get from environment first
        env_key = os.environ.get('ENCRYPTION_KEY')
        if env_key:
            try:
                self._encryption_key = base64.urlsafe_b64decode(env_key)
                return self._encryption_key
            except Exception:
                pass
        
        # Try to get from file in data folder
        key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', '.encryption_key')
        key_file = os.path.abspath(key_file)
        if os.path.exists(key_file):
            try:
                with open(key_file, 'rb') as f:
                    self._encryption_key = f.read()
                return self._encryption_key
            except Exception:
                pass
        
        # Generate new key and save it
        self._encryption_key = Fernet.generate_key()
        try:
            with open(key_file, 'wb') as f:
                f.write(self._encryption_key)
            os.chmod(key_file, 0o600)  # Restrict file permissions
        except Exception as e:
            print(f"Warning: Could not save encryption key to file: {e}")
        
        return self._encryption_key
    
    def encrypt_data(self, data: str) -> str:
        """
        Encrypt sensitive data (like API keys, secrets)
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        if not data:
            return ""
            
        key = self.get_encryption_key()
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Plain text data
        """
        if not encrypted_data:
            return ""
            
        try:
            key = self.get_encryption_key()
            f = Fernet(key)
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = f.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            print(f"Error decrypting data: {e}")
            return ""
    
    @staticmethod
    def generate_secure_api_key(length: int = 32) -> str:
        """
        Generate a cryptographically secure API key
        
        Args:
            length: Length of the API key in bytes
            
        Returns:
            URL-safe base64 encoded API key
        """
        return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode('utf-8')
    
    @staticmethod
    def is_password_secure(password: str) -> tuple[bool, list[str]]:
        """
        Check if a password meets security requirements
        
        Args:
            password: Password to check
            
        Returns:
            Tuple of (is_secure: bool, issues: list[str])
        """
        issues = []
        
        if len(password) < 12:
            issues.append("Password must be at least 12 characters long")
        
        if not any(c.isupper() for c in password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            issues.append("Password must contain at least one number")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            issues.append("Password must contain at least one special character")
        
        # Check for common weak passwords
        weak_passwords = ['password', '123456', 'admin', 'password123', 'qwerty']
        if password.lower() in weak_passwords:
            issues.append("Password is too common")
        
        return len(issues) == 0, issues

# Global instance
security_manager = SecurityManager()
