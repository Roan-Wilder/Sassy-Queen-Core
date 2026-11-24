#!/usr/bin/env python3
"""
SassyQueenCore Database Locking Handler
Overrides system SQLite access to prevent database locking issues
"""

import os
import sys
import sqlite3
import threading
import logging
import time
import queue
import atexit
from pathlib import Path
import inspect
import types

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'db_locking.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SassyQueenCore.DbLocking")

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Store the original sqlite3.connect function
original_sqlite3_connect = sqlite3.connect

class SingletonConnectionPool:
    """Singleton connection pool for SQLite database"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path=None, pool_size=3):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SingletonConnectionPool, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, db_path=None, pool_size=3):
        if self._initialized:
            return
            
        self.db_path = str(db_path or 'memory_database.db')
        self.pool_size = pool_size
        self.pool = queue.Queue(maxsize=pool_size)
        self.active_connections = 0
        self.pool_lock = threading.Lock()
        
        # Initialize connections
        for _ in range(pool_size):
            self._add_connection()
            
        # Register cleanup at exit
        atexit.register(self.close_all)
        
        logger.info(f"Connection pool initialized for {self.db_path} with {pool_size} connections")
        self._initialized = True
    
    def _add_connection(self):
        try:
            # Create a new connection with WAL mode
            conn = original_sqlite3_connect(self.db_path, check_same_thread=False, timeout=120.0)
            
            # Set WAL mode and optimize
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA busy_timeout=120000")  # Increased to 120 seconds timeout
            
            # Add to pool
            self.pool.put(conn)
            
            with self.pool_lock:
                self.active_connections += 1
                
            return True
        except Exception as e:
            logger.error(f"Error adding connection to pool: {e}")
            return False
    
    def get_connection(self, timeout=20):  # Increased timeout
        try:
            # Try to get a connection from the pool
            conn = self.pool.get(block=True, timeout=timeout)
            return conn
        except queue.Empty:
            # If pool is empty and we've reached max size, wait
            if self.active_connections >= self.pool_size:
                logger.warning("Connection pool exhausted, waiting for a connection")
                return self.get_connection(timeout)  # Retry
            
            # Otherwise, add a new connection
            with self.pool_lock:
                if self.active_connections < self.pool_size:
                    self._add_connection()
            
            # Try again
            return self.get_connection(timeout)
    
    def return_connection(self, conn):
        try:
            # Check if connection is valid
            try:
                conn.execute("SELECT 1")
                # Valid, return to pool
                self.pool.put(conn)
            except (sqlite3.Error, Exception):
                # Invalid, replace it
                conn.close()
                self._add_connection()
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
    
    def close_all(self):
        try:
            # Close all connections
            closed = 0
            while not self.pool.empty():
                try:
                    conn = self.pool.get(block=False)
                    conn.close()
                    closed += 1
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            
            with self.pool_lock:
                self.active_connections = 0
                
            logger.info(f"Closed {closed} database connections")
            return True
        except Exception as e:
            logger.error(f"Error closing connections: {e}")
            return False

# Global connection pool
_connection_pool = None

def get_connection_pool(db_path=None, pool_size=5):  # Increased pool size
    """Get the singleton connection pool"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = SingletonConnectionPool(db_path, pool_size)
    return _connection_pool

def safe_connect(database, *args, **kwargs):
    """Safe connect function that uses connection pooling"""
    try:
        # Use our connection pool for memory_database.db
        db_path = str(database)
        if "memory_database.db" in db_path or database == ":memory:":
            pool = get_connection_pool(db_path)
            return pool.get_connection()
        
        # For other databases, use the original connect with extended timeout
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 120.0  # Add a 120-second timeout if not specified
        return original_sqlite3_connect(database, *args, **kwargs)
    except Exception as e:
        logger.error(f"Error in safe_connect: {e}")
        # Fall back to original connect
        return original_sqlite3_connect(database, *args, **kwargs)

def execute_query(db_path, query, params=(), fetch_mode="all"):
    """Execute a query using the connection pool"""
    pool = get_connection_pool(db_path)
    conn = None
    retry_count = 0
    max_retries = 5  # Increased max retries
    
    while retry_count < max_retries:
        try:
            conn = pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                conn.commit()
                result = cursor.rowcount
            else:
                if fetch_mode == "all":
                    result = cursor.fetchall()
                elif fetch_mode == "one":
                    result = cursor.fetchone()
                else:
                    result = None
            
            pool.return_connection(conn)
            return result
        except sqlite3.OperationalError as e:
            # Handle locking errors with retries
            if "database is locked" in str(e) and retry_count < max_retries:
                retry_count += 1
                logger.warning(f"Database locked, retrying ({retry_count}/{max_retries})...")
                time.sleep(1.0 * retry_count)  # Longer exponential backoff
                if conn:
                    try:
                        # Try to rollback any pending transaction
                        conn.rollback()
                    except:
                        pass
                    pool.return_connection(conn)
            else:
                logger.error(f"Database error: {e}")
                if conn:
                    pool.return_connection(conn)
                return None
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            if conn:
                pool.return_connection(conn)
            return None
    
    logger.error(f"Failed to execute query after {max_retries} retries")
    return None

def override_sqlite3():
    """Override sqlite3.connect with our safe version"""
    try:
        # Replace sqlite3.connect with our safe version
        sqlite3.connect = safe_connect
        logger.info("Overrode sqlite3.connect with safe version")
        return True
    except Exception as e:
        logger.error(f"Error overriding sqlite3.connect: {e}")
        return False

def add_memory_functions(memory_module):
    """Add non-locking database functions to memory module"""
    try:
        if not memory_module:
            logger.warning("Memory module not provided")
            return False
            
        # Add execute_query function
        def module_execute_query(query, params=(), fetch_mode="all"):
            """Execute a query safely with the connection pool"""
            return execute_query("memory_database.db", query, params, fetch_mode)
            
        setattr(memory_module, "execute_query", module_execute_query)
        
        # Add execute function (common in memory module)
        if hasattr(memory_module, "execute"):
            original_execute = getattr(memory_module, "execute")
            
            def safe_execute(query, params=(), connection=None, fetch_mode="all"):
                """Safe version of execute that uses the connection pool"""
                return execute_query("memory_database.db", query, params, fetch_mode)
                
            setattr(memory_module, "execute", safe_execute)
            logger.info("Replaced memory module execute function")
        
        # Add special non-locking implementation of update_associations
        if hasattr(memory_module, "MemoryLearningPlugin"):
            plugin_class = getattr(memory_module, "MemoryLearningPlugin")
            
            if hasattr(plugin_class, "_update_associations"):
                # Create non-locking version
                def non_locking_update_associations(self, memory_id, related_ids, strength=0.5):
                    """Non-locking implementation of update_associations"""
                    try:
                        for related_id in related_ids:
                            # Try multiple times with backoff in case of locking
                            for attempt in range(5):  # Up to 5 attempts
                                try:
                                    # Use single atomic statement for each association
                                    execute_query("memory_database.db", """
                                    INSERT OR REPLACE INTO associations (source_id, target_id, strength, last_updated) 
                                    VALUES (?, ?, 
                                        COALESCE((SELECT (strength + ?) / 2 FROM associations 
                                                WHERE source_id = ? AND target_id = ?), ?),
                                        CURRENT_TIMESTAMP)
                                    """, (memory_id, related_id, strength, memory_id, related_id, strength))
                                    
                                    # Also create reverse association with half strength
                                    half_strength = strength / 2
                                    execute_query("memory_database.db", """
                                    INSERT OR REPLACE INTO associations (source_id, target_id, strength, last_updated) 
                                    VALUES (?, ?, 
                                        COALESCE((SELECT (strength + ?) / 2 FROM associations 
                                                WHERE source_id = ? AND target_id = ?), ?),
                                        CURRENT_TIMESTAMP)
                                    """, (related_id, memory_id, half_strength, related_id, memory_id, half_strength))
                                    
                                    # If we got here, it succeeded
                                    break
                                except Exception as e:
                                    if "database is locked" in str(e) and attempt < 4:
                                        # Sleep with backoff before retrying
                                        time.sleep(0.5 * (attempt + 1))
                                    else:
                                        logger.error(f"Error updating association after {attempt+1} attempts: {e}")
                                        break
                        
                        return True
                    except Exception as e:
                        logger.error(f"Error in non-locking update associations: {e}")
                        return False
                
                # Replace the method
                setattr(plugin_class, "_update_associations", non_locking_update_associations)
                logger.info("Replaced _update_associations with non-locking version")
        
        logger.info("Added non-locking database functions to memory module")
        return True
    except Exception as e:
        logger.error(f"Error adding memory functions: {e}")
        return False

def monkey_patch_sqlite():
    """Apply monkey patching to SQLite to prevent locking issues"""
    try:
        # Try to import gc
        try:
            import gc
        except ImportError:
            logger.warning("Could not import gc module")
            gc = None
            
        # First, override sqlite3.connect
        override_sqlite3()
        
        # Patch MemoryLearningPlugin if loaded
        for module_name in list(sys.modules.keys()):
            if "memory_learning" in module_name:
                memory_module = sys.modules[module_name]
                add_memory_functions(memory_module)
                logger.info(f"Applied memory functions to {module_name}")
        
        # Find all SQLite connections in memory and patch them
        patched = 0
        if gc:
            for obj in gc.get_objects():
                if isinstance(obj, sqlite3.Connection):
                    # For existing connections, best we can do is set busy timeout
                    try:
                        obj.execute("PRAGMA busy_timeout=120000")
                        patched += 1
                    except:
                        pass
        
            if patched > 0:
                logger.info(f"Patched {patched} existing SQLite connections")
            
        return True
    except Exception as e:
        logger.error(f"Error in monkey_patch_sqlite: {e}")
        return False

def main():
    """Main function"""
    try:
        # Import modules we might need
        try:
            import gc
        except ImportError:
            logger.warning("Could not import gc module")
            gc = None
        
        # Override SQLite connect function
        override_sqlite3()
        
        # Try to find and patch memory_learning module
        try:
            import plugins.memory_learning
            add_memory_functions(plugins.memory_learning)
            logger.info("Patched plugins.memory_learning module")
        except ImportError:
            try:
                import plugins.active.memory_learning
                add_memory_functions(plugins.active.memory_learning)
                logger.info("Patched plugins.active.memory_learning module")
            except ImportError:
                # Try searching sys.modules
                if gc:
                    # Apply monkey patching to find and patch all SQLite-related objects
                    monkey_patch_sqlite()
                else:
                    logger.warning("Could not find memory_learning module")
        
        print("Database locking handler installed")
        return 0
    except Exception as e:
        logger.error(f"Error in db_locking_handler: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 