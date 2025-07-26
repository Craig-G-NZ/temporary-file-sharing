import json
import os
from typing import Any, Dict, Optional
from app.utils.security import security_manager

class Settings:
    
    @staticmethod
    def get_db_path():
        """Get database connection"""
        try:
            from app.utils.database import get_db_connection
            return get_db_connection()
        except ImportError:
            return None
    
    @staticmethod
    def init_db():
        """Initialize settings table"""
        from app.utils.database import get_db_connection
        conn = get_db_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get setting value"""
        from app.utils.database import get_db_connection
        
        try:
            conn = get_db_connection()
            cursor = conn.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            
            return default
            
        except Exception as e:
            print(f"Error getting setting {key}: {e}")
            return default
    
    @staticmethod
    def set(key: str, value: Any, description: str = None) -> bool:
        """Set setting value"""
        from app.utils.database import get_db_connection
        
        try:
            conn = get_db_connection()
            
            # Get existing description if not provided
            if description is None:
                cursor = conn.execute('SELECT description FROM settings WHERE key = ?', (key,))
                row = cursor.fetchone()
                description = row[0] if row else key
            
            conn.execute('''
                INSERT OR REPLACE INTO settings (key, value, description, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, json.dumps(value), description))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error setting {key}: {e}")
            return False
    
    @staticmethod
    def set_encrypted(key: str, value: str, description: str = None) -> bool:
        """Set encrypted setting value for sensitive data"""
        if not value:
            return Settings.set(key, "", description)
        
        try:
            encrypted_value = security_manager.encrypt_data(value)
            # Store with a prefix to identify encrypted values
            return Settings.set(f"encrypted_{key}", encrypted_value, description)
        except Exception as e:
            print(f"Error setting encrypted setting {key}: {e}")
            return False
    
    @staticmethod
    def get_encrypted(key: str, default: str = "") -> str:
        """Get decrypted setting value for sensitive data"""
        try:
            encrypted_value = Settings.get(f"encrypted_{key}", "")
            if not encrypted_value:
                return default
            
            decrypted_value = security_manager.decrypt_data(encrypted_value)
            return decrypted_value if decrypted_value else default
        except Exception as e:
            print(f"Error getting encrypted setting {key}: {e}")
            return default
    
    @staticmethod
    def migrate_to_encrypted(key: str) -> bool:
        """Migrate a plain text setting to encrypted storage"""
        try:
            # Get current plain text value
            plain_value = Settings.get(key, "")
            if not plain_value:
                return True  # Nothing to migrate
            
            # Store encrypted version
            success = Settings.set_encrypted(key, plain_value)
            if success:
                # Remove old plain text version
                from app.utils.database import get_db_connection
                conn = get_db_connection()
                conn.execute('DELETE FROM settings WHERE key = ?', (key,))
                conn.commit()
                conn.close()
                print(f"INFO: Migrated setting '{key}' to encrypted storage")
                return True
            return False
        except Exception as e:
            print(f"Error migrating setting {key} to encrypted storage: {e}")
            return False
    
    @staticmethod
    def get_all() -> Dict[str, Dict]:
        """Get all settings"""
        from app.utils.database import get_db_connection
        
        try:
            conn = get_db_connection()
            cursor = conn.execute('SELECT key, value, description FROM settings')
            settings = {}
            
            for key, value_json, description in cursor.fetchall():
                try:
                    settings[key] = {
                        'value': json.loads(value_json),
                        'description': description
                    }
                except json.JSONDecodeError:
                    settings[key] = {
                        'value': value_json,
                        'description': description
                    }
            
            conn.close()
            return settings
            
        except Exception as e:
            print(f"Error getting all settings: {e}")
            return {}
    
    @staticmethod
    def get_max_file_size_bytes() -> int:
        """Get max file size in bytes"""
        max_gb = Settings.get('max_file_size_gb', 5)
        return int(max_gb * 1024 * 1024 * 1024)  # Convert GB to bytes
    
    @staticmethod
    def get_max_total_upload_bytes() -> int:
        """Get max total upload size in bytes"""
        max_gb = Settings.get('max_total_upload_gb', 20)
        return int(max_gb * 1024 * 1024 * 1024)  # Convert GB to bytes
    
    @staticmethod
    def get_email_config() -> Dict:
        """Get email configuration with encrypted sensitive data"""
        return {
            'api_key': Settings.get_encrypted('mailjet_api_key', ''),
            'api_secret': Settings.get_encrypted('mailjet_api_secret', ''),
            'from_email': Settings.get('mailjet_from_email', ''),
            'from_name': Settings.get('mailjet_from_name', 'Secure File Share')
        }
    
    @staticmethod
    def get_api_key() -> str:
        """Retrieve encrypted API key for external uploads"""
        return Settings.get_encrypted('api_key', '')

    @staticmethod
    def generate_api_key() -> str:
        """Generate and store a new encrypted API key"""
        key = security_manager.generate_secure_api_key()
        Settings.set_encrypted('api_key', key, 'API key for external uploads')
        return key

    @staticmethod
    def get_notification_email() -> str:
        """Get admin notification email address for API uploads"""
        return Settings.get('notification_email', '')

    @staticmethod
    def set_notification_email(email: str) -> bool:
        """Set admin notification email address for API uploads"""
        return Settings.set('notification_email', email, 'Admin notification email for upload alerts')
    
    @staticmethod
    def get_app_config() -> Dict:
        """Get application configuration"""
        return {
            'file_retention_hours': Settings.get('file_retention_hours', 24),
            'max_file_size_gb': Settings.get('max_file_size_gb', 5),
            'max_total_upload_gb': Settings.get('max_total_upload_gb', 20),
            'max_files_per_upload': Settings.get('max_files_per_upload', 10),
            'require_email': Settings.get('require_email', True),
            'auto_cleanup': Settings.get('auto_cleanup', True),
            'cleanup_interval_minutes': Settings.get('cleanup_interval_minutes', 60),
            'display_timezone': Settings.get('display_timezone', 'Pacific/Auckland'),
            'api_key': Settings.get_api_key(),
            'notification_email': Settings.get_notification_email()
        }
    
    @staticmethod
    def get_timezone_config() -> Dict:
        """Get timezone configuration"""
        return {
            'display_timezone': Settings.get('display_timezone', 'Pacific/Auckland'),
            'available_timezones': Settings.get_available_timezones()
        }
    
    @staticmethod
    def get_available_timezones() -> Dict:
        """Get available timezones for dropdown"""
        from app.utils.helpers import get_available_timezones
        return get_available_timezones()
    
    @staticmethod
    def set_display_timezone(timezone: str) -> bool:
        """Set display timezone"""
        # Validate timezone
        import pytz
        try:
            pytz.timezone(timezone)
            return Settings.set('display_timezone', timezone, 'Display timezone for dates and times')
        except:
            return False

    @staticmethod
    def is_configured() -> bool:
        """Check if basic configuration is complete"""
        email_config = Settings.get_email_config()
        return bool(email_config['api_key'] and email_config['api_secret'] and email_config['from_email'])
