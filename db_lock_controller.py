#!/usr/bin/env python3
"""
Database Lock Controller for SassyQueenCore
Controls database access to prevent lock conflicts
"""

import os
import sqlite3
import time
import logging
import random
import atexit
import threading
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SassyQueenCore.LockController")

# Global lock to ensure only one connection is made at a time
ACCESS_LOCK = threading.RLock()
DB_CONNECTIONS = {}
CONNECTION_OWNERS = {}

def get_exclusive_connection(db_path, owner_id="main", timeout=30):
    """
    Get an exclusive connection to the database
    
    Args:
        db_path: Path to the database
        owner_id: Identifier for the connection owner
        timeout: Connection timeout in seconds
        
    Returns:
        sqlite3.Connection: Database connection
    """
    global DB_CONNECTIONS, CONNECTION_OWNERS
    
    with ACCESS_LOCK:
        # Check if we already have a connection for this owner
        if owner_id in DB_CONNECTIONS and DB_CONNECTIONS[owner_id]:
            return DB_CONNECTIONS[owner_id]
        
        # Try to connect with retry
        for attempt in range(5):
            try:
                # Connect with exclusive access
                conn = sqlite3.connect(db_path, timeout=timeout, isolation_level="EXCLUSIVE")
                
                # Configure connection for reliability
                conn.execute("PRAGMA journal_mode = DELETE")  # Use DELETE mode instead of WAL for better lock handling
                conn.execute("PRAGMA synchronous = NORMAL")
                conn.execute("PRAGMA busy_timeout = 10000")
                conn.execute("PRAGMA temp_store = MEMORY")
                
                # Store the connection
                DB_CONNECTIONS[owner_id] = conn
                CONNECTION_OWNERS[conn] = owner_id
                
                logger.info(f"Created exclusive connection for {owner_id}")
                return conn
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 4:
                    delay = (attempt + 1) * 2 + random.random()
                    logger.warning(f"Database locked, retrying in {delay:.2f}s (attempt {attempt+1}/5)")
                    time.sleep(delay)
                else:
                    raise

def release_connection(owner_id):
    """
    Release a connection by owner ID
    
    Args:
        owner_id: The ID of the connection owner
    """
    global DB_CONNECTIONS, CONNECTION_OWNERS
    
    with ACCESS_LOCK:
        if owner_id in DB_CONNECTIONS:
            conn = DB_CONNECTIONS[owner_id]
            if conn:
                try:
                    conn.close()
                    logger.info(f"Closed connection for {owner_id}")
                except:
                    pass
                
                # Remove references
                if conn in CONNECTION_OWNERS:
                    del CONNECTION_OWNERS[conn]
                del DB_CONNECTIONS[owner_id]

def execute_query(db_path, query, params=None, fetch=None, owner_id="main"):
    """
    Execute a query using a managed connection
    
    Args:
        db_path: Path to the database
        query: SQL query to execute
        params: Parameters for the query
        fetch: What to fetch ('one', 'all', or None)
        owner_id: Owner ID for the connection
        
    Returns:
        Result of the query or None
    """
    conn = get_exclusive_connection(db_path, owner_id)
    
    try:
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        result = None
        if fetch == "one":
            result = cursor.fetchone()
        elif fetch == "all":
            result = cursor.fetchall()
        else:
            conn.commit()
            
        return result
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        try:
            conn.rollback()
        except:
            pass
        raise

def close_all_connections():
    """Close all open connections"""
    global DB_CONNECTIONS
    
    with ACCESS_LOCK:
        for owner_id in list(DB_CONNECTIONS.keys()):
            release_connection(owner_id)
    
    logger.info("Closed all database connections")

# Register cleanup function
atexit.register(close_all_connections)

# Function to patch modules
def patch_memory_module(memory_module, db_path):
    """
    Patch a memory module to use our connection management
    
    Args:
        memory_module: The memory module to patch
        db_path: Path to the database
    """
    # Create a patched connect function
    def patched_connect(*args, **kwargs):
        # Generate a unique owner ID for this call
        caller_frame = sys._getframe(1)
        caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"
        owner_id = f"memory_{hash(caller_info) % 10000}"
        
        return get_exclusive_connection(db_path, owner_id)
    
    # Replace the module's connection function if it has one
    if hasattr(memory_module, "connect_to_db"):
        memory_module.original_connect = memory_module.connect_to_db
        memory_module.connect_to_db = patched_connect
        
    # Add our functions to the module
    memory_module.get_exclusive_connection = get_exclusive_connection
    memory_module.release_connection = release_connection
    memory_module.execute_query = lambda q, p=None, f=None: execute_query(db_path, q, p, f)
    
    logger.info(f"Patched memory module with exclusive connection handling")

if __name__ == "__main__":
    print("Database Lock Controller initialized")
    print("Use this module to control database access and prevent lock conflicts") 