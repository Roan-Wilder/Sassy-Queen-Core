#!/usr/bin/env python3
"""
Database Rebuild Utility for SassyQueenCore
Completely rebuilds the database from scratch while preserving essential data
"""

import os
import sys
import sqlite3
import time
import logging
import shutil
import traceback
import argparse
from pathlib import Path
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SassyQueenCore.DBRebuild")

class DatabaseRebuild:
    """Class to rebuild the database from scratch"""
    
    def __init__(self):
        """Initialize the database rebuild utility"""
        self.base_dir = Path(__file__).resolve().parent
        self.db_path = self.base_dir / "memory_database.db"
        self.backup_path = self.base_dir / "memory_database.db.backup"
        self.temp_db_path = self.base_dir / "memory_database_new.db"
    
    def terminate_all_processes(self):
        """Forcefully terminate all Python processes"""
        logger.info("Terminating all Python processes")
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                time.sleep(2)  # Give time for processes to terminate
            else:  # Unix-like
                subprocess.run(["pkill", "-9", "python"], 
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                time.sleep(2)
        except Exception as e:
            logger.error(f"Error terminating processes: {e}")
    
    def remove_lock_files(self):
        """Remove all database lock files"""
        logger.info("Removing lock files")
        lock_files = [
            f"{self.db_path}-journal",
            f"{self.db_path}-wal",
            f"{self.db_path}-shm",
            f"{self.db_path}.lock"
        ]
        
        for lock_file in lock_files:
            try:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
                    logger.info(f"Removed lock file: {lock_file}")
            except Exception as e:
                logger.warning(f"Could not remove lock file: {e}")
    
    def backup_database(self):
        """Create a backup of the existing database"""
        logger.info("Creating database backup")
        try:
            if self.db_path.exists():
                # Create multiple backups with timestamps
                timestamp = int(time.time())
                timestamped_backup = self.base_dir / f"memory_database_{timestamp}.db.backup"
                
                try:
                    shutil.copy2(self.db_path, timestamped_backup)
                    logger.info(f"Created timestamped backup: {timestamped_backup}")
                except Exception as e:
                    logger.error(f"Error creating timestamped backup: {e}")
                
                # Try the regular backup
                try:
                    shutil.copy2(self.db_path, self.backup_path)
                    logger.info(f"Created backup: {self.backup_path}")
                    return True
                except Exception as e:
                    logger.error(f"Error creating regular backup: {e}")
            else:
                logger.warning("Database file doesn't exist, no backup created")
            
            return False
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False
    
    def extract_schema(self):
        """Extract schema from existing database or backup"""
        logger.info("Extracting database schema")
        
        source_db = None
        if self.db_path.exists():
            source_db = self.db_path
        elif self.backup_path.exists():
            source_db = self.backup_path
        
        if not source_db:
            logger.error("No source database found to extract schema")
            return None
        
        try:
            # Try to connect to the source database
            try:
                conn = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True, timeout=3)
            except sqlite3.OperationalError:
                logger.warning("Could not open database in read-only mode, trying normal mode")
                conn = sqlite3.connect(source_db, timeout=3)
            
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            schema = []
            for table in tables:
                table_name = table[0]
                if table_name.startswith('sqlite_'):
                    continue
                
                # Get table schema
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                table_sql = cursor.fetchone()[0]
                schema.append(table_sql)
                
                # Get indices for this table
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='{table_name}'")
                indices = cursor.fetchall()
                for idx in indices:
                    if idx[0]:  # Some indices might have NULL sql
                        schema.append(idx[0])
            
            conn.close()
            return schema
        except Exception as e:
            logger.error(f"Error extracting schema: {e}")
            traceback.print_exc()
            return None
    
    def create_new_database(self, schema):
        """Create a new database with the extracted schema"""
        logger.info("Creating new database")
        
        if not schema:
            logger.error("No schema provided, cannot create new database")
            return False
        
        try:
            # Make sure temp db doesn't exist
            if self.temp_db_path.exists():
                os.remove(self.temp_db_path)
            
            # Create new database
            conn = sqlite3.connect(self.temp_db_path)
            conn.isolation_level = None  # Autocommit mode
            
            # Set optimal pragmas
            conn.execute("PRAGMA journal_mode = DELETE")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.execute("PRAGMA page_size = 4096")
            
            # Execute schema statements
            for stmt in schema:
                try:
                    conn.execute(stmt)
                except sqlite3.OperationalError as e:
                    logger.warning(f"Error executing schema statement: {e}\nStatement: {stmt}")
                    # Continue with other statements
            
            conn.close()
            logger.info("New database created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating new database: {e}")
            traceback.print_exc()
            return False
    
    def create_empty_database(self):
        """Create a completely new empty database with basic structure"""
        logger.info("Creating new empty database")
        
        try:
            # Make sure temp db doesn't exist
            if self.temp_db_path.exists():
                os.remove(self.temp_db_path)
            
            # Create new database
            conn = sqlite3.connect(self.temp_db_path)
            conn.isolation_level = None  # Autocommit mode
            
            # Set optimal pragmas
            conn.execute("PRAGMA journal_mode = DELETE")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.execute("PRAGMA page_size = 4096")
            
            # Create basic tables that should exist in any SassyQueenCore database
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
            
            conn.close()
            logger.info("Empty database created successfully with basic tables")
            return True
        except Exception as e:
            logger.error(f"Error creating empty database: {e}")
            traceback.print_exc()
            return False
    
    def migrate_essential_data(self):
        """Migrate essential data from old database to new one"""
        logger.info("Migrating essential data")
        
        source_db = None
        if self.backup_path.exists():
            source_db = self.backup_path
        elif self.db_path.exists():
            source_db = self.db_path
        
        if not source_db:
            logger.warning("No source database found for migration")
            return False
        
        try:
            # Connect to source and destination databases
            try:
                src_conn = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True, timeout=3)
            except sqlite3.OperationalError:
                logger.warning("Could not open source in read-only mode, trying normal mode")
                src_conn = sqlite3.connect(source_db, timeout=3)
                
            dest_conn = sqlite3.connect(self.temp_db_path)
            
            src_cursor = src_conn.cursor()
            dest_cursor = dest_conn.cursor()
            
            # Get all tables from destination database
            dest_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = dest_cursor.fetchall()
            
            # For each table, try to copy data
            for table in tables:
                table_name = table[0]
                
                try:
                    # Check if table exists in source
                    src_cursor.execute(f"SELECT 1 FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                    if not src_cursor.fetchone():
                        logger.warning(f"Table {table_name} does not exist in source database")
                        continue
                    
                    # Get column names for this table
                    src_cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in src_cursor.fetchall()]
                    
                    if not columns:
                        logger.warning(f"No columns found for table {table_name}")
                        continue
                    
                    columns_str = ", ".join(columns)
                    placeholders = ", ".join(["?" for _ in columns])
                    
                    # Get data from source
                    try:
                        src_cursor.execute(f"SELECT {columns_str} FROM {table_name}")
                        rows = src_cursor.fetchall()
                        
                        # If we have data, insert into destination
                        if rows:
                            # Begin transaction
                            dest_conn.execute("BEGIN TRANSACTION")
                            
                            insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                            dest_cursor.executemany(insert_sql, rows)
                            
                            # Commit transaction
                            dest_conn.execute("COMMIT")
                            
                            logger.info(f"Migrated {len(rows)} rows from table {table_name}")
                    except sqlite3.OperationalError as e:
                        logger.warning(f"Error fetching data from {table_name}: {e}")
                        # Try to roll back if needed
                        try:
                            dest_conn.execute("ROLLBACK")
                        except:
                            pass
                        
                except Exception as e:
                    logger.warning(f"Error migrating table {table_name}: {e}")
                    # Try to roll back if needed
                    try:
                        dest_conn.execute("ROLLBACK")
                    except:
                        pass
            
            # Close connections
            src_conn.close()
            dest_conn.close()
            
            logger.info("Data migration completed")
            return True
        except Exception as e:
            logger.error(f"Error migrating data: {e}")
            traceback.print_exc()
            return False
    
    def replace_database(self):
        """Replace the old database with the new one"""
        logger.info("Replacing old database with new one")
        
        try:
            # Try to remove the old database
            if self.db_path.exists():
                try:
                    os.remove(self.db_path)
                    logger.info("Removed old database")
                except Exception as e:
                    logger.error(f"Could not remove old database: {e}")
                    return False
            
            # Move the new database to the old location
            shutil.move(self.temp_db_path, self.db_path)
            logger.info("Replaced database successfully")
            
            return True
        except Exception as e:
            logger.error(f"Error replacing database: {e}")
            traceback.print_exc()
            return False
    
    def rebuild(self, try_migrate=True, force=False):
        """Full database rebuild process"""
        logger.info(f"Starting database rebuild process (try_migrate={try_migrate}, force={force})")
        
        # Step 1: Terminate all processes
        self.terminate_all_processes()
        
        # Step 2: Remove lock files
        self.remove_lock_files()
        
        # Step 3: Backup existing database
        self.backup_database()
        
        # Step 4: Extract schema (if we're trying to migrate)
        if try_migrate:
            schema = self.extract_schema()
            if not schema:
                if force:
                    logger.warning("Failed to extract schema, creating empty database")
                    if not self.create_empty_database():
                        logger.error("Failed to create empty database, cannot proceed")
                        return False
                else:
                    logger.error("Failed to extract schema, cannot proceed")
                    return False
            else:
                # Step 5: Create new database
                if not self.create_new_database(schema):
                    if force:
                        logger.warning("Failed to create new database with schema, creating empty database")
                        if not self.create_empty_database():
                            logger.error("Failed to create empty database, cannot proceed")
                            return False
                    else:
                        logger.error("Failed to create new database, cannot proceed")
                        return False
                
                # Step 6: Migrate essential data
                self.migrate_essential_data()
        else:
            # Skip schema extraction and migration, just create empty database
            logger.info("Skipping migration, creating empty database")
            if not self.create_empty_database():
                logger.error("Failed to create empty database, cannot proceed")
                return False
        
        # Step 7: Replace old database with new one
        if not self.replace_database():
            logger.error("Failed to replace database")
            return False
        
        logger.info("Database rebuild completed successfully")
        return True

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="SassyQueenCore Database Rebuild Utility")
    parser.add_argument("--auto", action="store_true", help="Run in automatic mode without prompting")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if steps fail")
    parser.add_argument("--empty", action="store_true", help="Create an empty database without migration")
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()
    
    # Only print header in non-auto mode
    if not args.auto:
        print("SassyQueenCore Database Rebuild Utility")
        print("---------------------------------------")
    
    # Check if user wants to proceed (in non-auto mode)
    if not args.auto:
        response = input("This utility will rebuild your database from scratch. Continue? (y/n): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            return 1
    
    rebuilder = DatabaseRebuild()
    
    if not args.auto:
        print("\nStarting database rebuild process...")
    
    # Run the rebuild with appropriate options
    result = rebuilder.rebuild(try_migrate=not args.empty, force=args.force)
    
    if not args.auto:
        if result:
            print("\nDatabase rebuilt successfully!")
        else:
            print("\nDatabase rebuild failed. Check logs for details.")
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main()) 