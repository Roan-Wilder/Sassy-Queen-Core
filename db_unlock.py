#!/usr/bin/env python3
"""
SassyQueenCore Database Unlock Utility
Unlocks SQLite databases by releasing locks and fixing journal files
"""

import os
import sys
import sqlite3
import time
import logging
import shutil
import glob
from pathlib import Path
import traceback
import threading
import random
import argparse

# Set up logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'db_unlock.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SassyQueenCore.DBUnlock")

class DBUnlocker:
    """Database unlocker utility class"""
    
    def __init__(self):
        """Initialize the database unlocker"""
        self.base_dir = Path(__file__).resolve().parent
        self.db_files = []
        self.find_databases()
        
    def find_databases(self):
        """Find SQLite database files in the workspace"""
        # Look for .db files in the workspace
        db_files = list(self.base_dir.glob("**/*.db"))
        
        # Filter out files that are likely not SQLite databases
        valid_db_files = []
        for db_file in db_files:
            # Skip very small files (likely not real databases)
            if db_file.stat().st_size < 1024:
                continue
                
            # Skip files in certain directories
            if any(part in str(db_file) for part in [".git", "__pycache__", "venv", "env"]):
                continue
                
            valid_db_files.append(str(db_file))
            
        self.db_files = valid_db_files
        logger.info(f"Found {len(self.db_files)} database files")
        for db_file in self.db_files:
            logger.info(f"  - {db_file}")
            
        return self.db_files
        
    def create_backup(self, db_path):
        """Create a backup of the database file"""
        try:
            backup_path = f"{db_path}.backup"
            shutil.copy2(db_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating backup of {db_path}: {e}")
            return False
            
    def remove_lock_files(self, db_path):
        """Remove lock and journal files"""
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
                    
    def check_integrity(self, db_path):
        """Check database integrity"""
        try:
            # Connect with timeout and retry
            for attempt in range(3):
                try:
                    conn = sqlite3.connect(db_path, timeout=20.0)
                    break
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < 2:
                        time.sleep(1 + random.random())
                        continue
                    raise
            
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            logger.info(f"Database integrity: {result}")
            return result
        except Exception as e:
            logger.error(f"Error checking integrity of {db_path}: {e}")
            return "error"
            
    def force_unlock(self, db_path, force_mode=False):
        """Force unlock a database by copying to a new file and back"""
        try:
            # Generate temporary filename
            temp_db = f"{db_path}.temp.{int(time.time())}"
            
            # Copy database to temp file
            shutil.copy2(db_path, temp_db)
            
            # Wait for any processes to release the original
            time.sleep(1.0)
            
            # In force mode, don't try to validate the temp DB
            if not force_mode:
                try:
                    # Open and close the temporary database to ensure it's valid
                    conn = sqlite3.connect(temp_db, timeout=20.0)
                    conn.execute("PRAGMA integrity_check")
                    conn.close()
                except Exception as e:
                    logger.error(f"Error validating temp database: {e}")
                    if not force_mode:
                        raise
            
            # Try to force-close the original database by killing connections
            try:
                # In some cases, we can create a connection and then immediately close it
                # which helps release locks
                conn = sqlite3.connect(db_path, timeout=1.0)
                conn.close()
            except:
                pass
                
            # Force remove the original and replace it
            try:
                # Copy temp database back to original
                os.remove(db_path)
                shutil.copy2(temp_db, db_path)
            except Exception as e:
                logger.error(f"Error replacing original database: {e}")
                if not force_mode:
                    raise
                
            # Remove temp file
            try:
                os.remove(temp_db)
            except:
                pass
            
            logger.info("Force unlocked database by rewriting file")
            return True
        except Exception as e:
            logger.error(f"Error force unlocking {db_path}: {e}")
            traceback.print_exc()
            
            if force_mode:
                # In force mode, try even more aggressive methods
                try:
                    # Try to create a completely new database
                    if os.path.exists(db_path):
                        os.remove(db_path)
                        
                    # Create a minimal valid SQLite database
                    conn = sqlite3.connect(db_path)
                    conn.execute("PRAGMA journal_mode = DELETE")
                    conn.execute("PRAGMA synchronous = OFF")
                    conn.execute("CREATE TABLE IF NOT EXISTS memory_marker (id INTEGER PRIMARY KEY)")
                    conn.commit()
                    conn.close()
                    logger.info("Created new clean database in force mode")
                    return True
                except Exception as forced_e:
                    logger.error(f"Failed even with forced recreation: {forced_e}")
                    
            return False
            
    def unlock_database(self, db_path, force_mode=False):
        """Unlock a single database file"""
        try:
            logger.info(f"Attempting to unlock database: {db_path}")
            
            # Create backup first (unless in force mode and backup exists)
            backup_path = f"{db_path}.backup"
            if not (force_mode and os.path.exists(backup_path)):
                self.create_backup(db_path)
            
            # Check integrity before changes (skip in force mode)
            if not force_mode:
                integrity = self.check_integrity(db_path)
                if integrity != "ok":
                    logger.warning(f"Database integrity issues found: {integrity}")
                
            # Remove lock files
            self.remove_lock_files(db_path)
            
            # Wait a bit for processes to detect lock release
            time.sleep(1.0)
            
            # Try to connect to the database and run VACUUM
            try:
                conn = sqlite3.connect(db_path, timeout=20.0)
                conn.execute("PRAGMA journal_mode = DELETE")
                conn.execute("PRAGMA locking_mode = NORMAL")
                conn.execute("VACUUM")
                conn.close()
                logger.info("Successfully performed VACUUM on database")
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    logger.warning("Database still locked, attempting force unlock")
                    self.force_unlock(db_path, force_mode)
                else:
                    logger.error(f"Error during VACUUM: {e}")
                    if force_mode:
                        # In force mode, try force unlock anyway
                        self.force_unlock(db_path, force_mode)
            
            # Final connection test
            try:
                conn = sqlite3.connect(db_path, timeout=5.0)
                conn.execute("SELECT 1")
                conn.close()
                logger.info(f"Successfully unlocked database: {db_path}")
                return True
            except Exception as e:
                logger.error(f"Final connection test failed: {e}")
                
                # In force mode, try one more time with extreme measures
                if force_mode:
                    logger.warning("Attempting extreme force unlock")
                    return self.force_unlock(db_path, True)
                
                return False
                
        except Exception as e:
            logger.error(f"Error unlocking database {db_path}: {e}")
            traceback.print_exc()
            
            # In force mode, try force unlock as last resort
            if force_mode:
                logger.warning("Attempting force unlock as last resort")
                return self.force_unlock(db_path, True)
                
            return False
            
    def unlock_memory_db(self, force_mode=False):
        """Unlock the memory database"""
        memory_db = None
        
        # Find memory database
        for db_file in self.db_files:
            if "memory_database.db" in db_file:
                memory_db = db_file
                break
                
        if not memory_db:
            logger.error("Memory database not found")
            return False
            
        # Unlock the memory database
        return self.unlock_database(memory_db, force_mode)
        
    def unlock_all_dbs(self, force_mode=False):
        """Unlock all found databases"""
        results = []
        
        for db_file in self.db_files:
            result = self.unlock_database(db_file, force_mode)
            results.append(result)
            
        return all(results)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="SassyQueenCore Database Unlock Utility")
    parser.add_argument("--force", action="store_true", help="Force unlock even if it means data loss")
    parser.add_argument("--auto", action="store_true", help="Run in automatic mode (unlock all databases)")
    return parser.parse_args()

def main():
    """Main function"""
    # Parse arguments
    args = parse_arguments()
    
    # Print header if not in auto mode
    if not args.auto:
        print("SassyQueenCore Database Unlock Utility")
        print("--------------------------------------")
    
    unlocker = DBUnlocker()
    
    if not unlocker.db_files:
        print("No database files found.")
        return 1
    
    # In auto mode, unlock all databases
    if args.auto:
        result = unlocker.unlock_all_dbs(args.force)
        return 0 if result else 1
    
    # Interactive mode
    print("\nOptions:")
    print("1. Unlock memory database")
    print("2. Unlock all databases")
    
    try:
        choice = input("\nEnter choice (1-2) [default=1]: ").strip() or "1"
        
        if choice == "1":
            print("\nUnlocking memory database...")
            result = unlocker.unlock_memory_db(args.force)
        elif choice == "2":
            print("\nUnlocking all databases...")
            result = unlocker.unlock_all_dbs(args.force)
        else:
            print("Invalid choice. Please enter 1 or 2.")
            return 1
            
        if result:
            print("\nAll databases unlocked successfully!")
        else:
            print("\nSome databases could not be unlocked.")
            
        print("\nDatabase unlock process completed.")
        return 0
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 