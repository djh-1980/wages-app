"""
Settings model - handles settings and configuration database operations.
Extracted from web_app.py to improve code organization.
"""

from ..database import get_db_connection, execute_query
import json


class SettingsModel:
    """Model for settings and configuration operations."""
    
    @staticmethod
    def get_groupings():
        """Get client and job type groupings."""
        query = "SELECT value FROM settings WHERE key = 'groupings'"
        row = execute_query(query, fetch_one=True)
        
        if row:
            return json.loads(row['value'])
        else:
            return {'client_groups': {}, 'job_type_groups': {}}
    
    @staticmethod
    def save_groupings(groupings_data):
        """Save client and job type groupings."""
        query = """
            INSERT OR REPLACE INTO settings (key, value)
            VALUES ('groupings', ?)
        """
        execute_query(query, (json.dumps(groupings_data),))
        return True
    
    @staticmethod
    def get_setting(key):
        """Get a specific setting value."""
        query = "SELECT value FROM settings WHERE key = ?"
        row = execute_query(query, (key,), fetch_one=True)
        return row['value'] if row else None
    
    @staticmethod
    def set_setting(key, value):
        """Set a specific setting value."""
        query = """
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """
        execute_query(query, (key, value))
        return True
    
    @staticmethod
    def clear_all_settings():
        """Clear all settings."""
        query = "DELETE FROM settings"
        deleted = execute_query(query)
        return deleted
