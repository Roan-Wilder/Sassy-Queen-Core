#!/usr/bin/env python3
"""
SassyQueenCore Database Manager
Handles database connections with proper locking mechanisms
"""

import os
import sys
import sqlite3
import threading
import logging
import time
from pathlib import Path
import atexit

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'database.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SassyQueenCore.DatabaseManager")

class DatabaseConnectionPool:
    """SQLite connection pool to prevent database locking"""
    
    def __init__(self, db_path, max_connections=5, timeout=20):
        """Initialize the connection pool"""
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self.connections = []
        self.available_connections = []
        self.lock = threading.RLock()
        self.busy_wait_timeout = 30  # seconds
        
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        # Initialize connections
        self._init_connections()
        
        # Register cleanup
        atexit.register(self.close_all)
        
    def _init_connections(self):
        """Initialize connections in the pool"""
        with self.lock:
            for _ in range(self.max_connections):
                try:
                    # Create connection with extended timeout
                    conn = sqlite3.connect(
                        self.db_path, 
                        timeout=self.timeout,
                        check_same_thread=False,
                        isolation_level=None  # Autocommit mode
                    )
                    
                    # Enable WAL mode for better concurrency
                    conn.execute("PRAGMA journal_mode=WAL")
                    
                    # Set busy timeout
                    conn.execute(f"PRAGMA busy_timeout={self.timeout * 1000}")
                    
                    # Add connection to pool
                    self.connections.append(conn)
                    self.available_connections.append(conn)
                except sqlite3.Error as e:
                    logger.error(f"Error creating database connection: {e}")
        
        logger.info(f"Initialized database connection pool with {len(self.connections)} connections")
        
    def get_connection(self):
        """Get a connection from the pool"""
        start_time = time.time()
        
        while time.time() - start_time < self.busy_wait_timeout:
            with self.lock:
                if self.available_connections:
                    conn = self.available_connections.pop(0)
                    return conn
            
            # No connections available, wait and retry
            time.sleep(0.1)
        
        # If we get here, we couldn't get a connection in time
        raise TimeoutError("Timeout waiting for database connection")
        
    def release_connection(self, conn):
        """Release a connection back to the pool"""
        with self.lock:
            if conn in self.connections and conn not in self.available_connections:
                # Reset any lingering transactions
                try:
                    conn.execute("COMMIT")
                except sqlite3.Error:
                    try:
                        conn.execute("ROLLBACK")
                    except sqlite3.Error:
                        pass
                
                self.available_connections.append(conn)
                
    def close_all(self):
        """Close all connections in the pool"""
        with self.lock:
            for conn in self.connections:
                try:
                    conn.close()
                except sqlite3.Error as e:
                    logger.error(f"Error closing database connection: {e}")
            
            self.connections = []
            self.available_connections = []
            
        logger.info("Closed all database connections")


class DatabaseManager:
    """Manager for database operations with connection pooling"""
    
    def __init__(self, db_path=None):
        """Initialize the database manager"""
        if db_path is None:
            # Default to memory database in base directory
            base_dir = Path(__file__).resolve().parent
            self.db_path = os.path.join(base_dir, "memory_database.db")
        else:
            self.db_path = db_path
            
        # Create connection pool
        self.connection_pool = DatabaseConnectionPool(self.db_path)
        logger.info(f"Database manager initialized for {self.db_path}")
        
    def execute(self, query, params=None, fetch=None):
        """Execute a query with proper connection handling"""
        conn = None
        try:
            conn = self.connection_pool.get_connection()
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
                result = None
                
            return result
        except sqlite3.Error as e:
            logger.error(f"Database error: {e} in query: {query}")
            raise
        finally:
            if conn:
                self.connection_pool.release_connection(conn)
                
    def executemany(self, query, params_list):
        """Execute a query with multiple parameter sets"""
        conn = None
        try:
            conn = self.connection_pool.get_connection()
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
        except sqlite3.Error as e:
            logger.error(f"Database error in executemany: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.release_connection(conn)
                
    def execute_script(self, script):
        """Execute a SQL script"""
        conn = None
        try:
            conn = self.connection_pool.get_connection()
            conn.executescript(script)
        except sqlite3.Error as e:
            logger.error(f"Database error in execute_script: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.release_connection(conn)
    
    def transaction(self):
        """Get a transaction context manager"""
        return Transaction(self.connection_pool)
    
    def close(self):
        """Close all connections"""
        self.connection_pool.close_all()


class Transaction:
    """Context manager for database transactions"""
    
    def __init__(self, connection_pool):
        """Initialize the transaction"""
        self.connection_pool = connection_pool
        self.conn = None
        
    def __enter__(self):
        """Start the transaction"""
        self.conn = self.connection_pool.get_connection()
        self.conn.execute("BEGIN")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End the transaction"""
        if exc_type is None:
            # No exception, commit
            try:
                self.conn.execute("COMMIT")
            except sqlite3.Error as e:
                logger.error(f"Error committing transaction: {e}")
                try:
                    self.conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
        else:
            # Exception occurred, rollback
            try:
                self.conn.execute("ROLLBACK")
            except sqlite3.Error as e:
                logger.error(f"Error rolling back transaction: {e}")
                
        # Release the connection
        self.connection_pool.release_connection(self.conn)
        return False
        
    def execute(self, query, params=None, fetch=None):
        """Execute a query within the transaction"""
        cursor = self.conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        if fetch == "one":
            result = cursor.fetchone()
        elif fetch == "all":
            result = cursor.fetchall()
        else:
            result = None
            
        return result


# Singleton instance
_db_manager = None

def get_database_manager(db_path=None):
    """Get the singleton database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager

# Direct execution example
if __name__ == "__main__":
    # Create database manager
    db_manager = get_database_manager()
    
    # Create test table
    db_manager.execute("""
    CREATE TABLE IF NOT EXISTS test (
        id INTEGER PRIMARY KEY,
        name TEXT
    )
    """)
    
    # Insert test data
    db_manager.execute("INSERT INTO test (name) VALUES (?)", ("Test 1",))
    
    # Query test data
    result = db_manager.execute("SELECT * FROM test", fetch="all")
    print("Test data:", result)
    
    # Test transaction
    with db_manager.transaction() as transaction:
        transaction.execute("INSERT INTO test (name) VALUES (?)", ("Transaction Test",))
        
    # Close connections
    db_manager.close() 