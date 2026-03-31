"""
User model for authentication and authorization.
"""

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from ..database import get_db_connection, execute_query


class User(UserMixin):
    """User model for authentication."""
    
    def __init__(self, id, username, email, password_hash, is_active=True, is_admin=False, created_at=None, last_login=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self._is_active = is_active
        self.is_admin = is_admin
        self.created_at = created_at
        self.last_login = last_login
    
    @property
    def is_active(self):
        """Return whether user is active."""
        return bool(self._is_active)
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches hash."""
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        """Return user ID as string (required by Flask-Login)."""
        return str(self.id)
    
    def update_last_login(self):
        """Update last login timestamp."""
        query = "UPDATE users SET last_login = ? WHERE id = ?"
        execute_query(query, (datetime.now().isoformat(), self.id))
        self.last_login = datetime.now().isoformat()
    
    @staticmethod
    def create_user(username, email, password, is_admin=False):
        """
        Create a new user.
        
        Args:
            username: Username
            email: Email address
            password: Plain text password (will be hashed)
            is_admin: Whether user is admin
            
        Returns:
            User object or None if creation failed
        """
        password_hash = generate_password_hash(password)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, is_admin, is_active, created_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                """, (username, email, password_hash, is_admin, datetime.now().isoformat()))
                conn.commit()
                user_id = cursor.lastrowid
                
                return User.get_by_id(user_id)
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID."""
        query = "SELECT * FROM users WHERE id = ?"
        row = execute_query(query, (user_id,), fetch_one=True)
        
        if row:
            return User(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                password_hash=row['password_hash'],
                is_active=row['is_active'],
                is_admin=row['is_admin'],
                created_at=row['created_at'],
                last_login=row['last_login'] if 'last_login' in row.keys() else None
            )
        return None
    
    @staticmethod
    def get_by_username(username):
        """Get user by username."""
        query = "SELECT * FROM users WHERE username = ?"
        row = execute_query(query, (username,), fetch_one=True)
        
        if row:
            return User(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                password_hash=row['password_hash'],
                is_active=row['is_active'],
                is_admin=row['is_admin'],
                created_at=row['created_at'],
                last_login=row['last_login'] if 'last_login' in row.keys() else None
            )
        return None
    
    @staticmethod
    def get_by_email(email):
        """Get user by email."""
        query = "SELECT * FROM users WHERE email = ?"
        row = execute_query(query, (email,), fetch_one=True)
        
        if row:
            return User(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                password_hash=row['password_hash'],
                is_active=row['is_active'],
                is_admin=row['is_admin'],
                created_at=row['created_at'],
                last_login=row['last_login'] if 'last_login' in row.keys() else None
            )
        return None
    
    @staticmethod
    def get_all_users():
        """Get all users."""
        query = "SELECT * FROM users ORDER BY created_at DESC"
        rows = execute_query(query)
        
        users = []
        for row in rows:
            users.append(User(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                password_hash=row['password_hash'],
                is_active=row['is_active'],
                is_admin=row['is_admin'],
                created_at=row['created_at'],
                last_login=row.get('last_login')
            ))
        return users
    
    @staticmethod
    def update_user(user_id, **kwargs):
        """
        Update user details.
        
        Args:
            user_id: User ID
            **kwargs: Fields to update (username, email, is_active, is_admin)
        """
        allowed_fields = ['username', 'email', 'is_active', 'is_admin']
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        
        try:
            execute_query(query, tuple(values))
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    @staticmethod
    def change_password(user_id, new_password):
        """Change user password."""
        password_hash = generate_password_hash(new_password)
        query = "UPDATE users SET password_hash = ? WHERE id = ?"
        
        try:
            execute_query(query, (password_hash, user_id))
            return True
        except Exception as e:
            print(f"Error changing password: {e}")
            return False
    
    @staticmethod
    def delete_user(user_id):
        """Delete user (soft delete by setting is_active to False)."""
        query = "UPDATE users SET is_active = 0 WHERE id = ?"
        
        try:
            execute_query(query, (user_id,))
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    def to_dict(self):
        """Convert user to dictionary (excluding password hash)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at,
            'last_login': self.last_login
        }
