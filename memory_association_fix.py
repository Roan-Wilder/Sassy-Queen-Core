#!/usr/bin/env python3
"""
Memory Association Fix for SassyQueenCore
Fixes issues with memory associations and ensures the database is properly unlocked
"""

import os
import sys
import sqlite3
import time
import logging
import random
import contextlib
import threading
from pathlib import Path
import importlib

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SassyQueenCore.MemoryFix")

# Constants
DB_FILE = "memory_database.db"
MAX_RETRIES = 5
MAX_CONNECTIONS = 3  # Limit concurrent connections

# Thread local storage for database connections
local_storage = threading.local()

def get_db_manager():
    """Get the database manager instance, either from a module or create one"""
    try:
        # Try to import DatabaseManager from database_manager module
        from database_manager import DatabaseManager, get_database_manager
        return get_database_manager()
    except ImportError:
        try:
            # Try to import from memory_db_patch
            from memory_db_patch import get_db_manager
            return get_db_manager()
        except ImportError:
            logger.warning("No database manager module found, creating a basic one")
            # Create a simple connection
            db_path = get_db_path()
            return BasicDatabaseManager(db_path)

class BasicDatabaseManager:
    """Basic database manager if the full one isn't available"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.lock = threading.RLock()
        logger.info(f"Database manager initialized for {self.db_path}")
    
    def execute(self, query, params=None, fetch=None):
        """Execute a query with retry logic"""
        with self.lock:
            conn = None
            try:
                for attempt in range(MAX_RETRIES):
                    try:
                        # Increase timeout with each retry
                        timeout = 20.0 + (attempt * 5.0)
                        conn = sqlite3.connect(self.db_path, timeout=timeout)
                        
                        # Set pragmas for better concurrency
                        conn.execute("PRAGMA busy_timeout = 10000")
                        conn.execute("PRAGMA journal_mode = WAL")
                        conn.execute("PRAGMA synchronous = NORMAL")
                        
                        cursor = conn.cursor()
                        
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)
                        
                        if fetch == "one":
                            result = cursor.fetchone()
                        elif fetch == "all":
                            result = cursor.fetchall()
                        else:
                            result = cursor.rowcount
                            conn.commit()
                        
                        return result
                        
                    except sqlite3.OperationalError as e:
                        if "database is locked" in str(e) and attempt < MAX_RETRIES - 1:
                            # Add randomness to avoid lock collisions
                            jitter = random.uniform(0, 1.0)
                            delay = 2.0 + (attempt * 1.0) + jitter
                            
                            logger.warning(f"Database locked, retrying in {delay:.2f}s (attempt {attempt+1}/{MAX_RETRIES})")
                            if conn:
                                conn.close()
                            conn = None
                            time.sleep(delay)
                        else:
                            raise
            finally:
                if conn:
                    conn.close()
    
    def close_all(self):
        """Placeholder for compatibility"""
        pass

def get_db_path():
    """Get the path to the database file"""
    try:
        # Try to import DatabaseManager
        from database_manager import DatabaseManager
        db_manager = DatabaseManager()
        logger.info(f"Database manager found, using path: {db_manager.db_path}")
        return db_manager.db_path
    except ImportError:
        # Fall back to direct path
        logger.warning("Database manager not found, using direct connection")
        base_dir = Path(__file__).resolve().parent
        db_path = os.path.join(base_dir, DB_FILE)
        logger.info(f"Connecting to database at {db_path}")
        return db_path

def remove_lock_files(db_path):
    """Remove database lock files"""
    try:
        lock_files = [
            f"{db_path}-journal",
            f"{db_path}-wal",
            f"{db_path}-shm",
            f"{db_path}.lock"
        ]
        
        for lock_file in lock_files:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    logger.info(f"Removed lock file: {lock_file}")
                except PermissionError:
                    logger.warning(f"Cannot remove lock file (in use): {lock_file}")
                except Exception as e:
                    logger.error(f"Error removing lock file {lock_file}: {e}")
    except Exception as e:
        logger.error(f"Error in remove_lock_files: {e}")

def optimize_database(db_manager):
    """Optimize the database"""
    try:
        logger.info("Optimizing database")
        
        # Run VACUUM to defragment the database
        db_manager.execute("VACUUM")
        
        # Run integrity check
        integrity = db_manager.execute("PRAGMA integrity_check", fetch="one")
        if integrity and integrity[0] != "ok":
            logger.error(f"Database integrity check failed: {integrity[0]}")
            return False
        
        # Run optimization
        db_manager.execute("PRAGMA optimize")
        
        return True
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        return False

def fix_memory_associations():
    """Fix memory associations in the database with proper locking"""
    db_path = get_db_path()
    
    # First try to remove any lock files
    remove_lock_files(db_path)
    
    try:
        # Get a database manager
        db_manager = get_db_manager()
        
        # Optimize the database
        optimize_database(db_manager)
        
        # Find and fix any orphaned associations
        db_manager.execute("""
            DELETE FROM memory_associations 
            WHERE source_id NOT IN (SELECT memory_id FROM memories)
               OR target_id NOT IN (SELECT memory_id FROM memories)
        """)
        
        # Fix associations table if it exists
        db_manager.execute("""
            DELETE FROM associations 
            WHERE memory_id NOT IN (SELECT id FROM memories)
               OR associated_with_id NOT IN (SELECT id FROM memories)
        """)
        
        # Fix association strengths
        db_manager.execute("""
            UPDATE memory_associations
            SET strength = CASE
                WHEN strength < 0 THEN 0
                WHEN strength > 1 THEN 1
                ELSE strength
            END
            WHERE strength < 0 OR strength > 1
        """)
        
        # Fix strengths in associations table if it exists
        db_manager.execute("""
            UPDATE associations
            SET strength = CASE
                WHEN strength < 0 THEN 0
                WHEN strength > 1 THEN 1
                ELSE strength
            END
            WHERE strength < 0 OR strength > 1
        """)
        
        # Rebuild indices
        db_manager.execute("REINDEX")
        
        # Create new indices if needed
        db_manager.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_associations_source 
            ON memory_associations(source_id)
        """)
        
        db_manager.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_associations_target 
            ON memory_associations(target_id)
        """)
        
        # Add indices for associations table if it exists
        try:
            db_manager.execute("""
                CREATE INDEX IF NOT EXISTS idx_associations_memory 
                ON associations(memory_id)
            """)
            
            db_manager.execute("""
                CREATE INDEX IF NOT EXISTS idx_associations_associated 
                ON associations(associated_with_id)
            """)
        except:
            pass  # Table might not exist
        
        logger.info("Memory association fixes completed successfully")
        
        # Now patch the memory learning module if possible
        patch_memory_module()
        
        return True
        
    except Exception as e:
        logger.error(f"Error fixing memory associations: {e}")
        return False
    finally:
        # Clean up
        if 'db_manager' in locals() and hasattr(db_manager, 'close_all'):
            db_manager.close_all()

def patch_memory_module():
    """Patch the memory module with improved database connection handling"""
    try:
        # Try to find memory learning module
        memory_module = None
        
        # Check in different possible locations
        module_locations = [
            "plugins.memory_learning",
            "plugins.active.memory_learning",
            "memory_learning"
        ]
        
        for module_name in module_locations:
            try:
                memory_module = importlib.import_module(module_name)
                break
            except ImportError:
                continue
        
        if memory_module:
            # Find the MemoryLearningPlugin class
            for name in dir(memory_module):
                obj = getattr(memory_module, name)
                if isinstance(obj, type) and "Memory" in name:
                    cls = obj
                    
                    # Patch the _update_associations method
                    original_update = getattr(cls, "_update_associations", None)
                    if original_update:
                        def patched_update_associations(self):
                            """Patched version of update_associations that uses better connection handling"""
                            try:
                                # Use database manager if available
                                if hasattr(self, "db_manager"):
                                    db_manager = self.db_manager
                                elif hasattr(memory_module, "get_db_manager"):
                                    db_manager = memory_module.get_db_manager()
                                else:
                                    # Fall back to the original implementation
                                    return original_update(self)
                                
                                # Get all memories
                                memories = db_manager.execute('SELECT id, content FROM memories', fetch="all")
                                
                                # Process in smaller batches to avoid long locks
                                batch_size = 50
                                for i in range(0, len(memories), batch_size):
                                    batch = memories[i:i+batch_size]
                                    
                                    # Find and update associations (simplified approach)
                                    for j, mem1 in enumerate(batch):
                                        id1, content1 = mem1
                                        words1 = set(content1.lower().split())
                                        
                                        for mem2 in batch[j+1:]:
                                            id2, content2 = mem2
                                            words2 = set(content2.lower().split())
                                            
                                            # Calculate simple similarity
                                            common_words = words1.intersection(words2)
                                            if common_words:
                                                similarity = len(common_words) / max(len(words1), len(words2))
                                                
                                                if similarity > 0.2:  # Only associate if there's meaningful similarity
                                                    # Check if association already exists
                                                    existing = db_manager.execute(
                                                        '''
                                                        SELECT id, strength FROM associations
                                                        WHERE (memory_id = ? AND associated_with_id = ?) 
                                                           OR (memory_id = ? AND associated_with_id = ?)
                                                        ''', 
                                                        (id1, id2, id2, id1),
                                                        fetch="one"
                                                    )
                                                    
                                                    if existing:
                                                        # Update strength of existing association
                                                        assoc_id, strength = existing
                                                        new_strength = min(1.0, strength + 0.1)  # Increase strength, max 1.0
                                                        
                                                        db_manager.execute(
                                                            '''
                                                            UPDATE associations
                                                            SET strength = ?
                                                            WHERE id = ?
                                                            ''', 
                                                            (new_strength, assoc_id)
                                                        )
                                                    else:
                                                        # Create new association
                                                        db_manager.execute(
                                                            '''
                                                            INSERT INTO associations (memory_id, associated_with_id, strength)
                                                            VALUES (?, ?, ?)
                                                            ''', 
                                                            (id1, id2, similarity)
                                                        )
                                
                                logging.info("Memory associations updated with improved handling")
                                return True
                                
                            except Exception as e:
                                logging.error(f"Error in patched update_associations: {e}")
                                # Fall back to original method if our patch fails
                                return original_update(self)
                        
                        # Apply the patch
                        setattr(cls, "_update_associations", patched_update_associations)
                        logger.info(f"Patched method {name}._update_associations with improved database handling")
            
            return True
        else:
            logger.warning("Could not find memory module to patch")
            return False
    except Exception as e:
        logger.error(f"Error patching memory module: {e}")
        return False

def apply_association_patches():
    """Public function to apply memory association patches"""
    result = fix_memory_associations()
    print("Memory association fixes completed successfully" if result else "Failed to fix memory associations")
    return result

if __name__ == "__main__":
    apply_association_patches() 