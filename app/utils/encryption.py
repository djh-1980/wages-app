"""
Encryption utilities for sensitive data storage.
Uses Fernet (symmetric encryption) for token encryption.
"""

from cryptography.fernet import Fernet
import os
import base64
from pathlib import Path


class TokenEncryption:
    """Handle encryption/decryption of sensitive tokens."""
    
    def __init__(self):
        """Initialize encryption with key from environment or file."""
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self):
        """Get encryption key from environment or create new one."""
        # Try to get key from environment variable
        key_env = os.environ.get('ENCRYPTION_KEY')
        if key_env:
            return key_env.encode()
        
        # Try to get key from file
        key_file = Path('data/.encryption_key')
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        
        # Generate new key and save it
        key = Fernet.generate_key()
        
        # Create data directory if it doesn't exist
        key_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save key to file (with restricted permissions)
        with open(key_file, 'wb') as f:
            f.write(key)
        
        # Set file permissions to owner-only read/write
        os.chmod(key_file, 0o600)
        
        print(f"⚠️  NEW ENCRYPTION KEY GENERATED: {key_file}")
        print("⚠️  BACKUP THIS FILE - Without it, encrypted data cannot be decrypted!")
        
        return key
    
    def encrypt(self, plaintext):
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            str: Base64-encoded encrypted string
        """
        if plaintext is None:
            return None
        
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        
        encrypted = self.cipher.encrypt(plaintext)
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext):
        """
        Decrypt encrypted string.
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            str: Decrypted plaintext string
        """
        if ciphertext is None:
            return None
        
        try:
            encrypted = base64.b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return None


# Global instance
_encryption = None

def get_encryption():
    """Get global encryption instance."""
    global _encryption
    if _encryption is None:
        _encryption = TokenEncryption()
    return _encryption
