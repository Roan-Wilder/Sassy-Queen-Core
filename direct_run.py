#!/usr/bin/env python3
"""
SassyQueenCore Direct Runner
This script directly loads memory_learning and launches SassyQueenCore
with integrated mode switching and capability management
"""

import os
import sys
import io
import importlib.util
import importlib
from pathlib import Path
import traceback
import shutil
import json
import time
import logging
import types
import atexit
import sqlite3
import signal
import random

# CRITICAL: Import llama_cpp BEFORE PyQt6 to prevent access violation crashes
# This must happen before any PyQt6/QApplication imports occur
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'direct_run.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SassyQueenCore.DirectRun")

# Use lock controller if available
try:
    from db_lock_controller import get_exclusive_connection, release_connection, close_all_connections
    import db_lock_controller
    HAVE_LOCK_CONTROLLER = True
    logger.info("Using DB lock controller for connection management")
except ImportError:
    # Fall back to built-in connection management
    HAVE_LOCK_CONTROLLER = False
    logger.warning("DB lock controller not found, using fallback connection management")
    
    # Global tracking of database connections
    active_db_connections = []

    def register_db_connection(conn):
        """Register a database connection for cleanup on exit"""
        active_db_connections.append(conn)
        
    def close_all_db_connections():
        """Close all tracked database connections"""
        global active_db_connections
        
        if active_db_connections:
            logger.info(f"Closing {len(active_db_connections)} database connections")
            for conn in active_db_connections:
                try:
                    conn.close()
                    logger.info("Closed database connection")
                except Exception as e:
                    logger.error(f"Error closing database connection: {e}")
                    
            active_db_connections = []

def remove_lock_files(db_path):
    """Remove any lock files for a database"""
    try:
        lock_files = [
            f"{db_path}-journal",
            f"{db_path}-wal",
            f"{db_path}-shm",
            f"{db_path}.lock"
        ]
        
        for lock_file in lock_files:
            try:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
                    logger.info(f"Removed lock file: {lock_file}")
            except Exception as e:
                logger.warning(f"Could not remove lock file {lock_file}: {e}")
    except Exception as e:
        logger.error(f"Error removing lock files: {e}")

def connect_with_retry(db_path, max_retries=5, retry_delay=1):
    """Connect to a database with retries on lock errors"""
    # Use lock controller if available
    if HAVE_LOCK_CONTROLLER:
        # Generate a unique owner ID based on caller information
        caller_frame = sys._getframe(1)
        caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"
        owner_id = f"direct_{hash(caller_info) % 10000}"
        
        return get_exclusive_connection(db_path, owner_id)
    
    # Fall back to built-in retry logic
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            # Try to connect with increasing timeout
            timeout = 5.0 + (retries * 5.0)
            conn = sqlite3.connect(db_path, timeout=timeout)
            
            # Set pragmas for better lock handling
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("PRAGMA journal_mode = DELETE")
            conn.execute("PRAGMA locking_mode = NORMAL")
            
            # Register for cleanup
            if not HAVE_LOCK_CONTROLLER:
                register_db_connection(conn)
            
            logger.info(f"Successfully connected to database after {retries} retries")
            return conn
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                retries += 1
                last_error = e
                
                # Try to remove lock files
                remove_lock_files(db_path)
                
                # Add some randomness to avoid lock collisions
                jitter = random.uniform(0, 0.5)
                delay = retry_delay + (retries * 0.5) + jitter
                
                logger.warning(f"Database locked, retrying in {delay:.2f}s (attempt {retries}/{max_retries})")
                time.sleep(delay)
            else:
                raise
        except Exception as e:
            raise
    
    # If we get here, all retries failed
    logger.error(f"Failed to connect to database after {max_retries} retries")
    raise last_error or sqlite3.OperationalError("Database connection failed after retries")

def signal_handler(sig, frame):
    """Handle termination signals"""
    logger.info(f"Received signal {sig}, cleaning up...")
    if HAVE_LOCK_CONTROLLER:
        close_all_connections()
    else:
        close_all_db_connections()
    sys.exit(0)

# Register cleanup handlers
if HAVE_LOCK_CONTROLLER:
    # Lock controller already has atexit handler
    pass
else:
    atexit.register(close_all_db_connections)
    
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def ensure_directories_exist(base_dir):
    """Create necessary directories"""
    dirs = [
        "plugins", "plugins/active", "config", "logs", 
        "learning_data", "scripts", "security", "physical"
    ]
    
    for directory in dirs:
        dir_path = base_dir / directory
        dir_path.mkdir(exist_ok=True)
        
        # Create package __init__ files for Python directories
        if directory.startswith("plugins"):
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write("# Package initialization\n")
                    
    logger.info(f"Directory structure verified: {', '.join(dirs)}")

def unlock_databases(base_dir):
    """Unlock all databases before starting"""
    try:
        # Try to import the db_unlock module
        sys.path.insert(0, str(base_dir))
        
        try:
            import db_unlock
            unlocker = db_unlock.DBUnlocker()
            logger.info("Running database unlock utility...")
            
            # Unlock all databases with force option for reliability
            if unlocker.unlock_all_dbs(force_mode=True):
                logger.info("Successfully unlocked all databases")
                return True
            else:
                logger.warning("Some databases could not be unlocked")
                return False
        except ImportError:
            logger.warning("Could not import db_unlock module")
            return False
    except Exception as e:
        logger.error(f"Error unlocking databases: {e}")
        return False
        
def setup_memory_module(base_dir):
    """Set up the memory_learning module"""
    plugins_dir = base_dir / "plugins"
    active_dir = plugins_dir / "active"
    
    # Possible memory module locations
    memory_locations = [
        plugins_dir / "memory_learning.py",
        active_dir / "memory_learning.py",
        base_dir / "memory_learning.py"
    ]
    
    # Find existing memory module
    memory_file = None
    for loc in memory_locations:
        if loc.exists():
            memory_file = loc
            logger.info(f"Found memory_learning.py at: {loc}")
            break
    
    if memory_file:
        # Copy to both plugin locations if needed
        if memory_file != active_dir / "memory_learning.py":
            logger.info(f"Copying to active plugins: {active_dir}")
            shutil.copy2(memory_file, active_dir / "memory_learning.py")
            
        # Try to load the memory module using spec instead of exec
        try:
            # Create a proper module using importlib
            spec = importlib.util.spec_from_file_location(
                "plugins.memory_learning", 
                plugins_dir / "memory_learning.py"
            )
            
            if spec:
                memory_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(memory_module)
                
                # Register the module
                sys.modules['plugins.memory_learning'] = memory_module
                sys.modules['plugins.active.memory_learning'] = memory_module
                
                # Patch the module to use DB lock controller if available
                if HAVE_LOCK_CONTROLLER and hasattr(memory_module, 'connect_to_db'):
                    # Get the database path
                    db_path = None
                    try:
                        # Try to find database path from memory module
                        if hasattr(memory_module, 'DB_PATH'):
                            db_path = memory_module.DB_PATH
                        elif hasattr(memory_module, 'db_path'):
                            db_path = memory_module.db_path
                        else:
                            # Default to memory_database.db in base directory
                            db_path = os.path.join(base_dir, "memory_database.db")
                            
                        # Patch the module
                        db_lock_controller.patch_memory_module(memory_module, db_path)
                        logger.info("Patched memory module with DB lock controller")
                        
                    except Exception as e:
                        logger.error(f"Error patching memory module with lock controller: {e}")
                        
                        # Fall back to original connection wrapping
                        add_fallback_connection_handling(memory_module)
                else:
                    # Add fallback connection handling
                    add_fallback_connection_handling(memory_module)
                
                logger.info("Successfully loaded memory_learning module")
                return memory_module
                
        except Exception as e:
            logger.error(f"Error loading memory module: {e}")
            traceback.print_exc()
            
            # Try the old-style loading as fallback
            try:
                logger.info("Attempting fallback loading method")
                
                # Read the module file
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memory_learning_code = f.read()
                
                # Create a new module
                memory_module = types.ModuleType('memory_learning')
                
                # Add basic attributes
                memory_module.__file__ = str(memory_file)
                
                # Execute the code within the module's namespace
                module_globals = {'__name__': 'plugins.memory_learning', '__file__': str(memory_file)}
                
                exec(memory_learning_code, module_globals)
                
                # Update the module with the executed code
                for key, value in module_globals.items():
                    if key != "__builtins__":
                        setattr(memory_module, key, value)
                
                # Register the module
                sys.modules['plugins.memory_learning'] = memory_module
                sys.modules['plugins.active.memory_learning'] = memory_module
                
                # Add database connection handling
                if HAVE_LOCK_CONTROLLER and hasattr(memory_module, 'connect_to_db'):
                    # Get the database path
                    db_path = os.path.join(base_dir, "memory_database.db")
                    
                    # Patch the module
                    db_lock_controller.patch_memory_module(memory_module, db_path)
                    logger.info("Patched memory module with DB lock controller (fallback method)")
                else:
                    # Add fallback connection handling
                    add_fallback_connection_handling(memory_module)
                
                logger.info("Successfully loaded memory_learning module (fallback method)")
                return memory_module
                
            except Exception as inner_e:
                logger.error(f"Fallback loading also failed: {inner_e}")
                traceback.print_exc()
                return None
    else:
        logger.error("Memory learning module not found")
        return None

def add_fallback_connection_handling(memory_module):
    """Add fallback connection handling to memory module"""
    if hasattr(memory_module, 'connect_to_db'):
        original_connect = memory_module.connect_to_db
        
        # Create a wrapped connection function to track and properly close connections
        def wrapped_connect(*args, **kwargs):
            if len(args) > 0 and isinstance(args[0], str):
                # Try to use our retry connection for string paths
                try:
                    return connect_with_retry(args[0], **kwargs)
                except Exception:
                    # Fall back to original connect if our method fails
                    pass
            
            # Use original connection method
            conn = original_connect(*args, **kwargs)
            if isinstance(conn, sqlite3.Connection):
                if not HAVE_LOCK_CONTROLLER:
                    register_db_connection(conn)
            return conn
            
        # Replace the connection function
        memory_module.connect_to_db = wrapped_connect
        logger.info("Added database connection tracking to memory module")

def check_and_install_dependencies():
    """Check for and install required dependencies"""
    try:
        # Check for PyQt6
        try:
            import PyQt6
            logger.info("PyQt6 is already installed")
        except ImportError:
            logger.info("PyQt6 not found. Installing...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])
            import PyQt6
            
        return True
    except Exception as e:
        logger.error(f"Error installing dependencies: {e}")
        return False

def setup_mode_switcher(base_dir):
    """Initialize the mode switcher"""
    try:
        # Add base directory to path
        if str(base_dir) not in sys.path:
            sys.path.insert(0, str(base_dir))
            
        # Import mode switcher
        try:
            from mode_switcher import ModeSwitcher, get_mode_info
            switcher = ModeSwitcher()
            logger.info(f"Mode switcher initialized: {switcher.get_current_mode()} mode")
            return True
        except ImportError:
            logger.error("Mode switcher module not found.")
            return False
    except Exception as e:
        logger.error(f"Error setting up mode switcher: {e}")
        return False

def setup_capability_manager(base_dir):
    """Initialize the capability manager"""
    try:
        # Add base directory to path
        if str(base_dir) not in sys.path:
            sys.path.insert(0, str(base_dir))
            
        # Import capability manager
        try:
            from capability_manager import get_capability_manager
            manager = get_capability_manager()
            logger.info("Capability manager initialized")
            logger.info(f"Capabilities detected: {manager.capabilities}")
            return True
        except ImportError:
            logger.error("Capability manager module not found.")
            return False
    except Exception as e:
        logger.error(f"Error setting up capability manager: {e}")
        return False

def inject_system_prompt(base_dir):
    """Inject the system prompt into the LLM initialization"""
    try:
        system_prompt_file = base_dir / "system_prompt.txt"
        if system_prompt_file.exists():
            # Read the system prompt
            with open(system_prompt_file, "r", encoding="utf-8") as f:
                system_prompt = f.read()
                
            # Look for LLM integration files to inject the prompt
            scripts_dir = base_dir / "scripts"
            llm_integration_file = scripts_dir / "llm_integration.py"
            
            if llm_integration_file.exists():
                logger.info("System prompt will be injected into LLM integration")
                # The actual injection happens dynamically at runtime
                
            return True
        else:
            logger.warning("System prompt file not found")
            return False
    except Exception as e:
        logger.error(f"Error injecting system prompt: {e}")
        return False

def setup_memory_capabilities_bridge(base_dir):
    """Set up the memory capabilities bridge"""
    try:
        # Add base directory to path
        if str(base_dir) not in sys.path:
            sys.path.insert(0, str(base_dir))
        
        # Check if bridge file exists
        bridge_file = base_dir / "memory_capabilities_bridge.py"
        if not bridge_file.exists():
            logger.warning("Memory capabilities bridge file not found")
            return False
            
        # Import memory capabilities bridge
        try:
            # Use spec to load the module
            spec = importlib.util.spec_from_file_location(
                "memory_capabilities_bridge", 
                bridge_file
            )
            
            if spec:
                bridge_module = importlib.util.module_from_spec(spec)
                sys.modules["memory_capabilities_bridge"] = bridge_module
                spec.loader.exec_module(bridge_module)
                
                # Initialize the bridge
                bridge = bridge_module.get_memory_bridge()
                
                logger.info("Memory capabilities bridge initialized")
                
                # Try to inject functions into memory module if it exists
                if 'plugins.memory_learning' in sys.modules:
                    memory_module = sys.modules['plugins.memory_learning']
                    if bridge_module.inject_into_memory_module(memory_module):
                        logger.info("Successfully injected capability functions into memory module")
                    else:
                        logger.warning("Failed to inject capability functions")
                
                return True
            else:
                logger.error("Could not create spec for memory capabilities bridge")
                return False
        except Exception as e:
            logger.error(f"Error loading memory capabilities bridge: {e}")
            traceback.print_exc()
            return False
    except Exception as e:
        logger.error(f"Error setting up memory capabilities bridge: {e}")
        traceback.print_exc()
        return False

def launch_sassy_gui(base_dir):
    """Launch the SassyQueenCore GUI"""
    try:
        # Add scripts directory to path
        scripts_dir = base_dir / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        
        # Import using spec
        spec = importlib.util.spec_from_file_location(
            "sassy_gui", 
            scripts_dir / "sassy_gui.py"
        )
        
        if spec is None:
            logger.error("Error: Could not find sassy_gui.py")
            return False
            
        sassy_gui = importlib.util.module_from_spec(spec)
        sys.modules["sassy_gui"] = sassy_gui
        spec.loader.exec_module(sassy_gui)
        
        logger.info("Starting SassyQueenCore GUI...")
        
        # Check if we need to patch the main function to be capability and mode aware
        if hasattr(sassy_gui, 'main'):
            original_main = sassy_gui.main
            
            # Define a wrapped main function that's capability and mode aware
            def wrapped_main(*args, **kwargs):
                # Inject capabilities and mode information
                try:
                    # Update capabilities and mode status
                    from capability_manager import get_capability_manager
                    from mode_switcher import get_mode_info
                    
                    # Get latest information
                    capabilities = get_capability_manager().check_all_capabilities()
                    mode_info = get_mode_info()
                    
                    logger.info(f"Starting in {mode_info['current_mode']} mode")
                    logger.info(f"System capabilities: {capabilities}")
                    
                    # Refresh memory capabilities bridge if available
                    try:
                        import memory_capabilities_bridge
                        bridge = memory_capabilities_bridge.get_memory_bridge()
                        bridge.update_capability_info()
                        bridge.update_mode_info()
                        logger.info("Memory capabilities bridge updated before launch")
                    except ImportError:
                        logger.warning("Memory capabilities bridge not available for refresh")
                        
                except ImportError:
                    logger.warning("Could not update capabilities or mode before launch")
                    
                # Call the original main
                return original_main(*args, **kwargs)
                
            # Replace the main function
            sassy_gui.main = wrapped_main
            
        # Run the main function
        sassy_gui.main()
        return True
        
    except Exception as e:
        logger.error(f"Error launching SassyQueenCore GUI: {e}")
        traceback.print_exc()
        return False

def patch_sqlite3_module():
    """Patch the sqlite3 module to add retry functionality"""
    try:
        # Store the original connect function
        original_connect = sqlite3.connect
        
        # Create a patched version with retries
        def patched_connect(database, *args, **kwargs):
            if isinstance(database, str):
                # For string paths, use our retry connection
                try:
                    return connect_with_retry(database, *args, **kwargs)
                except Exception:
                    # Fall back to original if our method fails
                    pass
            
            # Use the original connection for other cases
            return original_connect(database, *args, **kwargs)
            
        # Replace the sqlite3 connect function
        sqlite3.connect = patched_connect
        logger.info("Patched sqlite3.connect with retry functionality")
        
        return True
    except Exception as e:
        logger.error(f"Error patching sqlite3 module: {e}")
        return False

def main():
    try:
        # Get base directory
        base_dir = Path(__file__).resolve().parent
        logger.info(f"Base directory: {base_dir}")
        
        # Add base directory to Python path
        sys.path.insert(0, str(base_dir))
        
        # Ensure required directories exist
        ensure_directories_exist(base_dir)
        
        # Patch sqlite3 module with retry functionality
        patch_sqlite3_module()
        
        # First unlock databases
        unlock_databases(base_dir)
        
        # Set up mode switcher
        mode_switcher_ready = setup_mode_switcher(base_dir)
        
        # Set up capability manager
        capability_manager_ready = setup_capability_manager(base_dir)
        
        # Set up memory module
        memory_ready = setup_memory_module(base_dir)
        if not memory_ready:
            logger.error("Failed to set up memory module")
            input("Press Enter to exit...")
            return False
        
        # Set up memory capabilities bridge
        setup_memory_capabilities_bridge(base_dir)
        
        # Check and install dependencies
        dependencies_ready = check_and_install_dependencies()
        if not dependencies_ready:
            logger.error("Failed to install required dependencies")
            input("Press Enter to exit...")
            return False
            
        # Inject system prompt
        inject_system_prompt(base_dir)
        
        # Launch SassyQueenCore
        gui_launched = launch_sassy_gui(base_dir)
        if not gui_launched:
            logger.error("Failed to launch SassyQueenCore GUI")
            input("Press Enter to exit...")
            return False
            
        return True
            
    except Exception as e:
        logger.error(f"Error in setup: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
        return False

if __name__ == "__main__":
    main() 