#!/usr/bin/env python3
"""
Enforce DELETE Journal Mode for SassyQueenCore Database
Forces the SQLite database to use DELETE journal mode instead of WAL
"""

import os
import sys
import sqlite3
import time
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SassyQueenCore.EnforceJournalMode")

def enforce_journal_mode(db_path):
    """Enforce DELETE journal mode on the database"""
    logger.info(f"Enforcing DELETE journal mode on {db_path}")
    
    try:
        # Connect to database with a long timeout
        conn = sqlite3.connect(db_path, timeout=10.0)
        
        # Get current journal mode
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        current_mode = cursor.fetchone()[0]
        logger.info(f"Current journal mode: {current_mode}")
        
        # Set optimal pragmas for avoiding locks
        cursor.execute("PRAGMA journal_mode = DELETE")
        new_mode = cursor.fetchone()[0]
        logger.info(f"New journal mode: {new_mode}")
        
        # Set other optimizations
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA locking_mode = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA cache_size = 2000")
        conn.execute("PRAGMA busy_timeout = 5000")
        
        # Commit changes and close
        conn.commit()
        conn.close()
        
        logger.info("Successfully enforced DELETE journal mode")
        return True
    except Exception as e:
        logger.error(f"Error enforcing journal mode: {e}")
        return False

def inject_journal_mode_hook():
    """Try to inject a hook into sqlite3 to enforce journal mode on every connection"""
    logger.info("Injecting journal mode hook into sqlite3")
    
    try:
        # Store the original connect function
        original_connect = sqlite3.connect
        
        # Create a wrapped version that enforces DELETE journal mode
        def wrapped_connect(*args, **kwargs):
            # Call the original connect
            connection = original_connect(*args, **kwargs)
            
            # Add pragmas to enforce journal mode
            try:
                connection.execute("PRAGMA journal_mode = DELETE")
                connection.execute("PRAGMA synchronous = NORMAL")
                connection.execute("PRAGMA busy_timeout = 5000")
            except:
                # Ignore errors in case this is a special connection
                pass
            
            return connection
        
        # Replace the sqlite3 connect function
        sqlite3.connect = wrapped_connect
        logger.info("Successfully injected journal mode hook")
        return True
    except Exception as e:
        logger.error(f"Error injecting journal mode hook: {e}")
        return False

def main():
    """Main function"""
    print("SassyQueenCore Journal Mode Enforcer")
    print("------------------------------------")
    
    # Get database path
    base_dir = Path(__file__).resolve().parent
    db_path = str(base_dir / "memory_database.db")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return 1
    
    print(f"Enforcing DELETE journal mode on {db_path}...")
    
    # Try to enforce journal mode
    success = enforce_journal_mode(db_path)
    
    # Try to inject hook
    hook_success = inject_journal_mode_hook()
    
    if success and hook_success:
        print("\nJournal mode successfully enforced!")
        print("This should help prevent database locking issues.")
        return 0
    else:
        print("\nError enforcing journal mode. Check logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 