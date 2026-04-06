"""
Database migration runner for TVS Wages.
Automatically applies SQL migrations on app startup.
"""

import os
import logging
from pathlib import Path
from ..database import get_db_connection

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Handles database schema migrations."""
    
    def __init__(self, migrations_dir=None):
        """
        Initialize migration runner.
        
        Args:
            migrations_dir: Path to migrations directory (defaults to migrations/ in project root)
        """
        if migrations_dir is None:
            # Default to migrations/ directory in project root
            project_root = Path(__file__).parent.parent.parent
            migrations_dir = project_root / 'migrations'
        
        self.migrations_dir = Path(migrations_dir)
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def _get_applied_migrations(self):
        """
        Get list of already applied migrations.
        
        Returns:
            set: Set of migration filenames that have been applied
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT filename FROM migrations ORDER BY id")
            return {row['filename'] for row in cursor.fetchall()}
    
    def _get_pending_migrations(self):
        """
        Get list of migrations that haven't been applied yet.
        
        Returns:
            list: Sorted list of migration filenames to apply
        """
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return []
        
        # Get all .sql files in migrations directory
        all_migrations = sorted([
            f.name for f in self.migrations_dir.glob('*.sql')
        ])
        
        # Get already applied migrations
        applied = self._get_applied_migrations()
        
        # Return only pending migrations
        pending = [m for m in all_migrations if m not in applied]
        
        return pending
    
    def _apply_migration(self, filename):
        """
        Apply a single migration file.
        
        Args:
            filename: Name of migration file to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        migration_path = self.migrations_dir / filename
        
        try:
            # Read migration SQL
            with open(migration_path, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            logger.info(f"Applying migration: {filename}")
            
            # Apply migration in a transaction
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Execute migration SQL
                # Split by semicolon to handle multiple statements
                statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
                
                for statement in statements:
                    cursor.execute(statement)
                
                # Record migration as applied
                cursor.execute(
                    "INSERT INTO migrations (filename) VALUES (?)",
                    (filename,)
                )
                
                conn.commit()
            
            logger.info(f"Migration complete: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {filename}")
            logger.error(f"Error: {e}", exc_info=True)
            return False
    
    def run_migrations(self):
        """
        Run all pending migrations.
        
        Returns:
            tuple: (success: bool, applied_count: int)
        """
        pending = self._get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations")
            return True, 0
        
        logger.info(f"Found {len(pending)} pending migration(s)")
        
        applied_count = 0
        for migration in pending:
            success = self._apply_migration(migration)
            
            if not success:
                logger.error(f"Migration failed, stopping migration process")
                return False, applied_count
            
            applied_count += 1
        
        logger.info(f"Successfully applied {applied_count} migration(s)")
        return True, applied_count


def run_migrations():
    """
    Convenience function to run migrations.
    Called from app initialization.
    
    Returns:
        tuple: (success: bool, applied_count: int)
    """
    runner = MigrationRunner()
    success, count = runner.run_migrations()
    return success, count
