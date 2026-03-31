#!/usr/bin/env python3
"""
Script to create the first admin user for the TVS Wages application.
Run this once to set up your admin account.
"""

import sys
import os
from getpass import getpass

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.user import User
from app.database import init_database

def create_admin():
    """Create admin user interactively."""
    print("=" * 60)
    print("TVS Wages - Create Admin User")
    print("=" * 60)
    print()
    
    # Initialize database
    print("Initializing database...")
    init_database()
    print("✓ Database initialized")
    print()
    
    # Get user details
    print("Enter admin user details:")
    print()
    
    username = input("Username: ").strip()
    if not username:
        print("❌ Username cannot be empty")
        return
    
    # Check if username exists
    if User.get_by_username(username):
        print(f"❌ Username '{username}' already exists")
        return
    
    email = input("Email: ").strip()
    if not email:
        print("❌ Email cannot be empty")
        return
    
    # Check if email exists
    if User.get_by_email(email):
        print(f"❌ Email '{email}' already exists")
        return
    
    password = getpass("Password (min 8 characters): ")
    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return
    
    password_confirm = getpass("Confirm password: ")
    if password != password_confirm:
        print("❌ Passwords do not match")
        return
    
    print()
    print("Creating admin user...")
    
    # Create user
    user = User.create_user(
        username=username,
        email=email,
        password=password,
        is_admin=True
    )
    
    if user:
        print()
        print("=" * 60)
        print("✓ Admin user created successfully!")
        print("=" * 60)
        print()
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Admin: Yes")
        print()
        print("You can now log in at: http://localhost:5001/login")
        print()
    else:
        print("❌ Failed to create user")

if __name__ == '__main__':
    try:
        create_admin()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
