import sqlite3
import os
from typing import Optional

# Database file path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'app_data.db')
DB_PATH = os.path.abspath(DB_PATH)

def get_db_connection() -> sqlite3.Connection:
    """Get database connection"""
    # Ensure the directory exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def init_database():
    """Initialize all database tables"""
    conn = get_db_connection()
    
    # Settings table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Admin users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # File shares table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS file_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            recipient_email TEXT NOT NULL,
            files TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            downloaded BOOLEAN DEFAULT 0,
            download_count INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print("INFO: Database tables initialized successfully")

def close_db_connection(conn: sqlite3.Connection):
    """Close database connection"""
    if conn:
        conn.close()
