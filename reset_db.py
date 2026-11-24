#!/usr/bin/env python3
"""
Database Complete Reset Script for SassyQueenCore
Creates a fresh, empty database with optimal settings to prevent locking
"""

import os
import sys
import sqlite3
import time
import logging
import subprocess
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SassyQueenCore.ResetDB")

def kill_python_processes():
    """Kill all Python processes that might be holding locks"""
    logger.info("Terminating all Python processes")
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            time.sleep(2)
        else:
            subprocess.run(["pkill", "-9", "python"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            time.sleep(2)
    except Exception as e:
        logger.error(f"Error terminating processes: {e}")

def remove_db_files(db_path):
    """Remove database and all related files"""
    files_to_remove = [
        db_path,
        f"{db_path}-journal",
        f"{db_path}-wal",
        f"{db_path}-shm",
        f"{db_path}.lock",
    ]
    
    for file_path in files_to_remove:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Removed {file_path}")
        except Exception as e:
            logger.error(f"Error removing {file_path}: {e}")

def create_fresh_database(db_path):
    """Create a fresh database with optimal settings"""
    logger.info(f"Creating fresh database: {db_path}")
    
    try:
        # Create connection
        conn = sqlite3.connect(db_path)
        
        # Set optimal pragmas for avoiding locks
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA locking_mode = NORMAL")
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("PRAGMA cache_size = 2000")
        conn.execute("PRAGMA temp_store = MEMORY")
        
        # Create basic tables
        conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            memory_id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            source TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            importance REAL DEFAULT 0.5,
            context TEXT,
            last_accessed DATETIME
        )
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_associations (
            association_id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            strength REAL DEFAULT 0.5,
            association_type TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES memories(memory_id),
            FOREIGN KEY (target_id) REFERENCES memories(memory_id)
        )
        """)
        
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_memory_associations_source ON memory_associations(source_id);
        """)
        
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_memory_associations_target ON memory_associations(target_id);
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_patterns (
            pattern_id INTEGER PRIMARY KEY,
            pattern TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            confidence REAL DEFAULT 0.5,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Commit changes and close
        conn.commit()
        conn.close()
        
        logger.info("Fresh database created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False

def main():
    """Main function"""
    print("SassyQueenCore Database Reset Tool")
    print("----------------------------------")
    
    # Get database path
    base_dir = Path(__file__).resolve().parent
    db_path = str(base_dir / "memory_database.db")
    
    # Confirm with user
    print(f"\nThis will delete ALL data in {db_path} and create a fresh database.")
    response = input("Are you sure you want to proceed? (y/n): ")
    
    if response.lower() != 'y':
        print("Operation cancelled.")
        return 1
    
    print("\nResetting database...")
    
    # Kill any Python processes
    kill_python_processes()
    
    # Remove existing database files
    remove_db_files(db_path)
    
    # Create fresh database
    if create_fresh_database(db_path):
        print("\nDatabase reset successfully!")
        print("All existing memories have been deleted.")
        print("The system will create a fresh database with optimal settings.")
        return 0
    else:
        print("\nError resetting database. Check logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 