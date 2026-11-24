#!/usr/bin/env python3
"""
SassyQueenCore Database Schema Fix
Ensures the database has the correct schema for non-locking operations
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'db_schema_fix.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SassyQueenCore.SchemaFix")

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def discover_table_structure(conn, table_name):
    """Discover the structure of a table"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Format: (cid, name, type, notnull, dflt_value, pk)
        column_names = [col[1] for col in columns]
        logger.info(f"Table {table_name} has columns: {column_names}")
        return column_names
    except Exception as e:
        logger.error(f"Error discovering table structure: {e}")
        return []

def main():
    """Main function"""
    try:
        # Find the memory database
        db_path = None
        possible_paths = [
            Path('memory_database.db'), 
            Path('../memory_database.db'),
            Path('plugins/memory_database.db')
        ]
        
        for path in possible_paths:
            if path.exists():
                db_path = path
                logger.info(f"Found database at {path}")
                break
        
        if not db_path:
            logger.warning("Could not find memory database, using default path")
            db_path = Path('memory_database.db')
        
        # Connect directly
        logger.info(f"Connecting to database at {db_path}")
        conn = sqlite3.connect(db_path)
        
        # Set WAL journal mode
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        
        # Get all tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Database contains tables: {tables}")
        
        # Check if memories table exists - this is the main table
        if 'memories' not in tables:
            logger.info("Creating memories table")
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY,
                content TEXT,
                importance REAL DEFAULT 0.5,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT,
                tags TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp);
            CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
            """)
            conn.commit()
            logger.info("Created memories table and indexes")
        
        # Check if the associations table exists
        if 'associations' not in tables:
            logger.info("Creating associations table")
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS associations (
                id INTEGER PRIMARY KEY,
                source_id INTEGER,
                target_id INTEGER,
                strength REAL DEFAULT 0.5,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES memories(id),
                FOREIGN KEY (target_id) REFERENCES memories(id),
                UNIQUE(source_id, target_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_associations_source ON associations(source_id);
            CREATE INDEX IF NOT EXISTS idx_associations_target ON associations(target_id);
            """)
            conn.commit()
            logger.info("Created associations table and indexes")
        else:
            # Discover the structure of the associations table
            columns = discover_table_structure(conn, 'associations')
            
            # Check if we need to add source_id and target_id columns
            if 'source_id' not in columns:
                logger.info("Adding source_id column to associations table")
                conn.execute("ALTER TABLE associations ADD COLUMN source_id INTEGER")
                conn.commit()
            
            if 'target_id' not in columns:
                logger.info("Adding target_id column to associations table")
                conn.execute("ALTER TABLE associations ADD COLUMN target_id INTEGER")
                conn.commit()
            
            # Check if last_updated column exists
            if 'last_updated' not in columns:
                logger.info("Adding last_updated column to associations table")
                conn.execute("ALTER TABLE associations ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                conn.commit()
            
            # Check if strength column exists
            if 'strength' not in columns:
                logger.info("Adding strength column to associations table")
                conn.execute("ALTER TABLE associations ADD COLUMN strength REAL DEFAULT 0.5")
                conn.commit()
                
            # Recreate indexes just to be sure
            logger.info("Ensuring indexes exist")
            conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_associations_source ON associations(source_id);
            CREATE INDEX IF NOT EXISTS idx_associations_target ON associations(target_id);
            """)
            conn.commit()
            
            # Make sure we have a UNIQUE constraint - trickier since we need to rebuild the table
            cursor.execute("PRAGMA index_list('associations')")
            has_unique = False
            for idx_info in cursor.fetchall():
                if len(idx_info) > 3 and idx_info[3] == 1:  # is_unique flag in newer SQLite
                    has_unique = True
                    break
                # For older SQLite versions, check index name
                elif "autoindex" in idx_info[1].lower():
                    has_unique = True
                    break
            
            if not has_unique:
                logger.info("Adding unique constraint to associations table")
                
                # First, drop the associations_new table if it already exists
                if 'associations_new' in tables:
                    logger.info("Dropping existing associations_new table")
                    conn.execute("DROP TABLE associations_new")
                    conn.commit()
                
                # Create a new table with the constraint
                conn.executescript("""
                CREATE TABLE associations_new (
                    id INTEGER PRIMARY KEY,
                    source_id INTEGER,
                    target_id INTEGER,
                    strength REAL DEFAULT 0.5,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES memories(id),
                    FOREIGN KEY (target_id) REFERENCES memories(id),
                    UNIQUE(source_id, target_id)
                );
                """)
                
                # Copy data - select only columns that exist in the old table
                column_list = ", ".join([c for c in ["id", "source_id", "target_id", "strength", "last_updated"] if c in columns])
                try:
                    conn.execute(f"INSERT OR IGNORE INTO associations_new ({column_list}) SELECT {column_list} FROM associations")
                    conn.commit()
                    
                    # Drop old table
                    conn.execute("DROP TABLE associations")
                    
                    # Rename new table
                    conn.execute("ALTER TABLE associations_new RENAME TO associations")
                    
                    # Recreate indexes
                    conn.executescript("""
                    CREATE INDEX IF NOT EXISTS idx_associations_source ON associations(source_id);
                    CREATE INDEX IF NOT EXISTS idx_associations_target ON associations(target_id);
                    """)
                    conn.commit()
                    logger.info("Added unique constraint to associations table")
                except Exception as e:
                    logger.error(f"Error copying data to new associations table: {e}")
                    conn.execute("DROP TABLE IF EXISTS associations_new")
                    conn.commit()
        
        # Optimize the database
        logger.info("Optimizing database")
        conn.execute("PRAGMA optimize")
        conn.execute("ANALYZE")
        
        # Close connection
        conn.close()
        
        logger.info("Database schema updated successfully")
        print("Database schema updated successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 