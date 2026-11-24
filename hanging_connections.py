#!/usr/bin/env python3
"""
Hanging Database Connections Detector and Fixer for SassyQueenCore
Detects and fixes hanging database connections
"""

import os
import sys
import sqlite3
import subprocess
import time
import logging
import psutil
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SassyQueenCore.HangingConnections")

class ConnectionDetector:
    """Class to detect and fix hanging database connections"""
    
    def __init__(self):
        """Initialize the connection detector"""
        self.base_dir = Path(__file__).resolve().parent
        self.db_path = self.base_dir / "memory_database.db"
    
    def find_open_handles(self):
        """Find processes with open handles to the database"""
        logger.info(f"Finding processes with open handles to {self.db_path}")
        
        db_processes = []
        db_path_str = str(self.db_path).lower()
        
        try:
            # Get all processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Skip non-Python processes
                    if not proc.name().lower() in ['python.exe', 'python', 'pythonw.exe']:
                        continue
                    
                    # Check open files for this process
                    proc_info = proc.as_dict(['pid', 'name', 'cmdline'])
                    try:
                        open_files = proc.open_files()
                        for file in open_files:
                            if db_path_str in file.path.lower():
                                db_processes.append(proc_info)
                                logger.info(f"Found process {proc.pid} with open handle to database")
                                break
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass
                    
                    # Also check the command line for the database path
                    if proc.cmdline() and any(db_path_str in cmd.lower() for cmd in proc.cmdline() if isinstance(cmd, str)):
                        if proc_info not in db_processes:
                            db_processes.append(proc_info)
                            logger.info(f"Found process {proc.pid} likely using database (from cmdline)")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return db_processes
        except Exception as e:
            logger.error(f"Error finding open handles: {e}")
            return []
    
    def terminate_processes(self, processes):
        """Terminate processes with open handles to the database"""
        if not processes:
            logger.info("No processes to terminate")
            return
        
        logger.info(f"Terminating {len(processes)} processes with open handles")
        
        for proc in processes:
            try:
                pid = proc['pid']
                logger.info(f"Terminating process {pid} ({proc['name']})")
                
                try:
                    # Try graceful termination first
                    process = psutil.Process(pid)
                    process.terminate()
                    
                    # Wait for process to terminate
                    gone, alive = psutil.wait_procs([process], timeout=2)
                    if process in alive:
                        # Force kill if still alive
                        process.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # If we can't terminate via psutil, try platform-specific commands
                    if os.name == 'nt':  # Windows
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                                      stdout=subprocess.DEVNULL, 
                                      stderr=subprocess.DEVNULL)
                    else:  # Unix-like
                        subprocess.run(['kill', '-9', str(pid)], 
                                      stdout=subprocess.DEVNULL, 
                                      stderr=subprocess.DEVNULL)
            except Exception as e:
                logger.error(f"Error terminating process {proc['pid']}: {e}")
    
    def remove_lock_files(self):
        """Remove database lock files"""
        logger.info("Removing database lock files")
        
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
                logger.warning(f"Could not remove lock file {lock_file}: {e}")
    
    def fix_journal_mode(self):
        """Fix database journal mode to DELETE"""
        logger.info("Fixing database journal mode")
        
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            
            # Set journal mode to DELETE for better compatibility
            conn.execute("PRAGMA journal_mode = DELETE")
            conn.execute("PRAGMA synchronous = NORMAL")
            
            # Commit and close
            conn.commit()
            conn.close()
            
            logger.info("Fixed database journal mode")
            return True
        except Exception as e:
            logger.error(f"Error fixing journal mode: {e}")
            return False
    
    def detect_and_fix(self):
        """Detect and fix hanging connections"""
        logger.info("Starting detection and fixing of hanging connections")
        
        # Step 1: Find processes with open handles
        processes = self.find_open_handles()
        
        if processes:
            # Step 2: Terminate those processes
            self.terminate_processes(processes)
            
            # Step 3: Wait a bit for processes to fully terminate
            time.sleep(2)
        else:
            logger.info("No processes found with open handles to the database")
        
        # Step 4: Remove any lock files
        self.remove_lock_files()
        
        # Step 5: Fix journal mode
        self.fix_journal_mode()
        
        logger.info("Completed fixing hanging connections")

def main():
    """Main function"""
    print("SassyQueenCore Hanging Connections Detector and Fixer")
    print("---------------------------------------------------")
    
    try:
        # Check if psutil is installed
        try:
            import psutil
        except ImportError:
            print("Installing required dependency: psutil")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
            import psutil
        
        detector = ConnectionDetector()
        detector.detect_and_fix()
        
        print("Successfully fixed hanging connections!")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 