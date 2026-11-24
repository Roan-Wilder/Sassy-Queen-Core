#!/usr/bin/env python3
"""
Database Lock Manager for SassyQueenCore
Continuously monitors for database locks and automatically resolves them
"""

import os
import sys
import time
import sqlite3
import logging
import threading
import subprocess
import psutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SassyQueenCore.LockManager")

# Constants
DB_FILE = "memory_database.db"
CHECK_INTERVAL = 10  # seconds
MAX_RETRIES = 3
MONITOR_RUNNING = True

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
        logger.info("Database manager not found, using direct path")
        base_dir = Path(__file__).resolve().parent
        db_path = os.path.join(base_dir, DB_FILE)
        logger.info(f"Using database at {db_path}")
        return db_path

def check_db_locked(db_path):
    """Check if the database is currently locked"""
    try:
        # Try a quick query with a short timeout
        conn = sqlite3.connect(db_path, timeout=1.0)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        return False
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            return True
        return False
    except Exception:
        return False

def find_locking_processes(db_path):
    """Find processes that might be locking the database"""
    locking_pids = []
    
    try:
        # Find all Python processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Skip our own process
                if proc.pid == os.getpid():
                    continue
                
                # Check if it's a Python process
                if "python" in proc.name().lower():
                    # Check if it has open handles to our database
                    for open_file in proc.open_files():
                        if db_path.lower() in open_file.path.lower():
                            locking_pids.append(proc.pid)
                            logger.info(f"Found process {proc.pid} locking database")
                            break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        logger.error(f"Error finding locking processes: {e}")
    
    return locking_pids

def unlock_database():
    """Try to unlock the database"""
    db_path = get_db_path()
    
    # Check if the database is actually locked
    if not check_db_locked(db_path):
        return True
    
    logger.info("Database is locked, attempting to fix")
    
    # First, try to find and terminate locking processes
    locking_pids = find_locking_processes(db_path)
    for pid in locking_pids:
        try:
            # Try to terminate the process
            process = psutil.Process(pid)
            process.terminate()
            logger.info(f"Terminated process {pid} that was locking the database")
        except Exception as e:
            logger.error(f"Error terminating process {pid}: {e}")
    
    # Give processes time to terminate
    time.sleep(1)
    
    # If still locked, try to run the database unlock utility
    if check_db_locked(db_path):
        try:
            logger.info("Running database unlock utility")
            # Try to import and run db_unlock directly
            try:
                import db_unlock
                db_unlock.unlock_databases(force=True)
            except ImportError:
                # Fall back to subprocess call
                subprocess.run([sys.executable, "db_unlock.py", "--force", "--auto"], 
                              check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            logger.error(f"Error running database unlock utility: {e}")
    
    # Try memory association fix as a last resort
    if check_db_locked(db_path):
        try:
            logger.info("Running memory association fix")
            # Try to import and run directly
            try:
                import memory_association_fix
                memory_association_fix.apply_association_patches()
            except ImportError:
                # Fall back to subprocess call
                subprocess.run([sys.executable, "memory_association_fix.py"], 
                              check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            logger.error(f"Error running memory association fix: {e}")
    
    # Check if we succeeded
    if not check_db_locked(db_path):
        logger.info("Successfully unlocked database")
        return True
    else:
        logger.error("Failed to unlock database after multiple attempts")
        return False

def monitor_thread_func():
    """Background thread function to monitor for database locks"""
    while MONITOR_RUNNING:
        try:
            # Check for database locks
            db_path = get_db_path()
            if check_db_locked(db_path):
                unlock_database()
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"Error in monitor thread: {e}")
            time.sleep(CHECK_INTERVAL)

def start_lock_monitor():
    """Start the background monitor thread"""
    global MONITOR_RUNNING
    MONITOR_RUNNING = True
    
    monitor_thread = threading.Thread(target=monitor_thread_func)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    logger.info("Database lock monitor started")
    return monitor_thread

def stop_lock_monitor():
    """Stop the monitor thread"""
    global MONITOR_RUNNING
    MONITOR_RUNNING = False
    logger.info("Database lock monitor stopped")

def initialize():
    """Initialize the database lock manager"""
    # Close any existing connections
    try:
        from database_manager import get_database_manager
        db_manager = get_database_manager()
        db_manager.close_all()
        logger.info("Closed all database connections")
    except ImportError:
        pass
    
    # Start the monitor thread
    monitor_thread = start_lock_monitor()
    
    # Unlock any currently locked databases
    unlock_database()
    
    return monitor_thread

if __name__ == "__main__":
    # When run directly, start the monitor
    monitor_thread = initialize()
    
    try:
        # Keep the script running
        print("Database lock monitor running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Stop the monitor when interrupted
        stop_lock_monitor()
        print("Database lock monitor stopped.")
    except Exception as e:
        logger.error(f"Error in main thread: {e}")
        stop_lock_monitor() 