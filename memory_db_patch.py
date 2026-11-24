#!/usr/bin/env python3
"""
Memory Database Patch for SassyQueenCore
Patches memory-related database functions to prevent locking issues
"""

import os
import sys
import importlib
import importlib.util
import sqlite3
import time
import logging
import inspect
import random
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SassyQueenCore.MemoryPatch")

# Database connection pool for reusing connections
class DatabaseManager:
    """Database connection manager with connection pooling"""
    
    def __init__(self, db_path=None, pool_size=5):
        """Initialize the database manager"""
        # Set database path
        if db_path is None:
            base_dir = Path(__file__).resolve().parent
            self.db_path = os.path.join(base_dir, "memory_database.db")
        else:
            self.db_path = db_path
        
        # Create connection pool
        self.pool_size = pool_size
        self.connection_pool = []
        self.initialize_pool()
        
        logger.info(f"Initialized database connection pool with {pool_size} connections")
        logger.info(f"Database manager initialized for {self.db_path}")
    
    def initialize_pool(self):
        """Initialize the connection pool"""
        for _ in range(self.pool_size):
            conn = self.create_connection()
            self.connection_pool.append(conn)
    
    def create_connection(self):
        """Create a new database connection with optimal settings"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        
        # Set pragmas for better performance and reliability
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA cache_size = 5000")
        
        return conn
    
    def get_connection(self):
        """Get a connection from the pool or create a new one"""
        if self.connection_pool:
            return self.connection_pool.pop()
        else:
            # All connections in use, create a new one
            return self.create_connection()
    
    def release_connection(self, conn):
        """Return a connection to the pool"""
        if len(self.connection_pool) < self.pool_size:
            # Only add back to pool if under size limit
            self.connection_pool.append(conn)
        else:
            # Pool is full, close this connection
            conn.close()
    
    def execute(self, query, params=None, fetch=None):
        """Execute a query with connection management"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Get results if requested
            if fetch == "one":
                result = cursor.fetchone()
            elif fetch == "all":
                result = cursor.fetchall()
            else:
                result = None
                conn.commit()
            
            return result
        except sqlite3.Error as e:
            if conn:
                # Try to rollback on error
                try:
                    conn.rollback()
                except:
                    pass
            logger.error(f"Database error: {e} in query: {query}")
            raise
        finally:
            if conn:
                self.release_connection(conn)
    
    def close_all(self):
        """Close all connections in the pool"""
        for conn in self.connection_pool:
            try:
                conn.close()
            except:
                pass
        
        self.connection_pool = []
        logger.info("Closed all database connections")

# Global database manager instance
_db_manager = None

def get_db_manager():
    """Get the global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

def patched_execute(original_func, *args, **kwargs):
    """Patched version of execute functions with retry logic"""
    max_retries = 5
    base_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            return original_func(*args, **kwargs)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                # Calculate delay with exponential backoff and jitter
                jitter = random.uniform(0, 1.0)
                delay = base_delay * (2 ** attempt) + jitter
                
                logger.warning(f"Database locked in {original_func.__name__}, retrying in {delay:.2f}s (attempt {attempt+1}/{max_retries})")
                time.sleep(delay)
            else:
                raise
        except Exception as e:
            logger.error(f"Error in {original_func.__name__}: {e}")
            raise

def patch_memory_module():
    """Patch the memory learning module with improved database handling"""
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
        
        if not memory_module:
            # Try to find the file directly
            for plugin_dir in ["plugins", "."]:
                memory_path = Path(__file__).resolve().parent / plugin_dir / "memory_learning.py"
                if memory_path.exists():
                    # Load from file path
                    spec = importlib.util.spec_from_file_location("memory_learning", memory_path)
                    memory_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(memory_module)
                    break
        
        if not memory_module:
            logger.error("Could not find memory learning module")
            return False
        
        logger.info(f"Memory module found: {memory_module}")
        
        # Add database utility functions
        memory_module.get_db_manager = get_db_manager
        logger.info("Added database utility functions to memory module")
        
        # Patch methods that interact with the database
        # 1. Patch standalone functions
        functions_to_patch = []
        for name, obj in inspect.getmembers(memory_module):
            if inspect.isfunction(obj) and name.startswith("_") and not name.startswith("__"):
                if "execute" in name or "connect" in name or "query" in name or "memory" in name or "db" in name:
                    functions_to_patch.append((name, obj))
        
        for name, func in functions_to_patch:
            # Create a wrapper that uses our patched_execute
            def create_wrapper(original_func):
                def wrapper(*args, **kwargs):
                    return patched_execute(original_func, *args, **kwargs)
                wrapper.__name__ = original_func.__name__
                wrapper.__doc__ = original_func.__doc__
                return wrapper
            
            # Apply the patch
            setattr(memory_module, name, create_wrapper(func))
            logger.info(f"Patched function {name}")
        
        # 2. Patch class methods
        for cls_name, cls in inspect.getmembers(memory_module, inspect.isclass):
            if "Memory" in cls_name or "DB" in cls_name or "Database" in cls_name:
                methods_to_patch = []
                
                for method_name, method in inspect.getmembers(cls, inspect.isfunction):
                    if method_name.startswith("_") and not method_name.startswith("__"):
                        if "execute" in method_name or "connect" in method_name or "query" in method_name or "memory" in method_name or "db" in method_name:
                            methods_to_patch.append((method_name, method))
                
                for method_name, method in methods_to_patch:
                    # Create a wrapper that uses our patched_execute
                    def create_method_wrapper(original_method):
                        def wrapper(*args, **kwargs):
                            return patched_execute(original_method, *args, **kwargs)
                        wrapper.__name__ = original_method.__name__
                        wrapper.__doc__ = original_method.__doc__
                        return wrapper
                    
                    # Apply the patch
                    setattr(cls, method_name, create_method_wrapper(method))
                    logger.info(f"Patched method {cls_name}.{method_name}")
        
        # 3. Patch specific known methods
        specific_methods = [
            "_clean_old_memories",
            "_consolidate_memories",
            "_forget_memories",
            "_initialize_database",
            "_recall_memories",
            "_report_learnings",
            "_report_memory_stats",
            "_save_learned_patterns", 
            "_store_memory",
            "_update_associations",
            "execute"
        ]
        
        memory_class = None
        for cls_name, cls in inspect.getmembers(memory_module, inspect.isclass):
            if "MemoryLearningPlugin" in cls_name:
                memory_class = cls
                break
        
        if memory_class:
            for method_name in specific_methods:
                if hasattr(memory_class, method_name):
                    original_method = getattr(memory_class, method_name)
                    
                    # Create a wrapper that uses our patched_execute
                    def create_method_wrapper(original_method):
                        def wrapper(*args, **kwargs):
                            return patched_execute(original_method, *args, **kwargs)
                        wrapper.__name__ = original_method.__name__
                        wrapper.__doc__ = original_method.__doc__
                        return wrapper
                    
                    # Apply the patch
                    setattr(memory_class, method_name, create_method_wrapper(original_method))
                    logger.info(f"Patched method {memory_class.__name__}.{method_name}")
        
        # Count patches applied
        patch_count = len(functions_to_patch)
        for cls_name, cls in inspect.getmembers(memory_module, inspect.isclass):
            if "Memory" in cls_name or "DB" in cls_name or "Database" in cls_name:
                for method_name, method in inspect.getmembers(cls, inspect.isfunction):
                    if method_name.startswith("_") and not method_name.startswith("__"):
                        if "execute" in method_name or "connect" in method_name or "query" in method_name or "memory" in method_name or "db" in method_name:
                            patch_count += 1
        
        logger.info(f"Applied {patch_count} patches to memory module")
        print("Successfully applied memory system patches")
        return True
    
    except Exception as e:
        logger.error(f"Error patching memory module: {e}")
        print(f"Error patching memory module: {e}")
        return False

def apply_memory_patches():
    """Apply all memory-related patches"""
    try:
        result = patch_memory_module()
        
        # Close database connections when the script exits
        db_manager = get_db_manager()
        db_manager.close_all()
        
        return result
    except Exception as e:
        logger.error(f"Error applying memory patches: {e}")
        return False

if __name__ == "__main__":
    apply_memory_patches() 