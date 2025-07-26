import os
import pytz
from datetime import datetime
from typing import Union

def format_file_size(bytes_size: Union[int, float]) -> str:
    """Format file size in human readable format"""
    if bytes_size == 0:
        return "0 B"
    
    size_units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(bytes_size)
    unit_index = 0
    
    while size >= 1024.0 and unit_index < len(size_units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:  # Bytes
        return f"{int(size)} {size_units[unit_index]}"
    else:
        return f"{size:.2f} {size_units[unit_index]}"

def validate_file_size(file_size_bytes: int, max_size_gb: float) -> bool:
    """Validate file size against GB limit"""
    max_size_bytes = max_size_gb * 1024 * 1024 * 1024
    return file_size_bytes <= max_size_bytes

def gb_to_bytes(gb: float) -> int:
    """Convert GB to bytes"""
    return int(gb * 1024 * 1024 * 1024)

def bytes_to_gb(bytes_size: int) -> float:
    """Convert bytes to GB"""
    return bytes_size / (1024 * 1024 * 1024)

def calculate_upload_progress(current_bytes: int, total_bytes: int) -> float:
    """Calculate upload progress percentage"""
    if total_bytes == 0:
        return 0.0
    return min(100.0, (current_bytes / total_bytes) * 100.0)

def is_file_size_valid(file_path: str, max_gb: float) -> bool:
    """Check if file size is within GB limits"""
    try:
        if not os.path.exists(file_path):
            return False
        
        file_size = os.path.getsize(file_path)
        max_bytes = gb_to_bytes(max_gb)
        
        return file_size <= max_bytes
    except:
        return False

def get_directory_size_gb(directory_path: str) -> float:
    """Get total size of directory in GB"""
    total_size = 0
    
    if not os.path.exists(directory_path):
        return 0.0
    
    for dirpath, dirnames, filenames in os.walk(directory_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except:
                pass
    
    return bytes_to_gb(total_size)


# Timezone utility functions

def get_available_timezones():
    """Get a list of common timezones for the dropdown"""
    return {
        'Pacific/Auckland': 'New Zealand (Auckland)',
        'Pacific/Chatham': 'New Zealand (Chatham Islands)',
        'Australia/Sydney': 'Australia (Sydney)',
        'Australia/Melbourne': 'Australia (Melbourne)',
        'Australia/Perth': 'Australia (Perth)',
        'Asia/Tokyo': 'Japan (Tokyo)',
        'Asia/Singapore': 'Singapore',
        'Asia/Shanghai': 'China (Shanghai)',
        'Asia/Hong_Kong': 'Hong Kong',
        'Asia/Kolkata': 'India (Kolkata)',
        'Europe/London': 'United Kingdom (London)',
        'Europe/Paris': 'France (Paris)',
        'Europe/Berlin': 'Germany (Berlin)',
        'Europe/Rome': 'Italy (Rome)',
        'UTC': 'UTC (Coordinated Universal Time)',
        'US/Eastern': 'US Eastern Time',
        'US/Central': 'US Central Time',
        'US/Mountain': 'US Mountain Time',
        'US/Pacific': 'US Pacific Time',
        'Canada/Eastern': 'Canada Eastern Time',
        'Canada/Pacific': 'Canada Pacific Time',
    }

def get_user_timezone():
    """Get the user's configured timezone from settings"""
    from app.models.settings import Settings
    timezone_str = Settings.get('display_timezone', 'Pacific/Auckland')
    
    try:
        return pytz.timezone(timezone_str)
    except:
        # Fallback to Auckland if invalid timezone
        return pytz.timezone('Pacific/Auckland')

def convert_utc_to_user_timezone(utc_datetime):
    """Convert UTC datetime to user's configured timezone"""
    if utc_datetime is None:
        return None
    
    # If the datetime is naive (no timezone info), assume it's UTC
    if utc_datetime.tzinfo is None:
        utc_datetime = pytz.utc.localize(utc_datetime)
    
    # Convert to user's timezone
    user_tz = get_user_timezone()
    user_datetime = utc_datetime.astimezone(user_tz)
    return user_datetime

def format_datetime_user_timezone(utc_datetime, format_str='%d/%m/%Y %H:%M %Z'):
    """Format UTC datetime as user's timezone string"""
    if utc_datetime is None:
        return "Not set"
    
    user_datetime = convert_utc_to_user_timezone(utc_datetime)
    return user_datetime.strftime(format_str)

def format_date_user_timezone(utc_datetime, format_str='%d/%m/%Y'):
    """Format UTC datetime as user's timezone date string"""
    if utc_datetime is None:
        return "Not set"
    
    user_datetime = convert_utc_to_user_timezone(utc_datetime)
    return user_datetime.strftime(format_str)

def get_current_user_time():
    """Get current time in user's timezone"""
    user_tz = get_user_timezone()
    return datetime.now(user_tz)
