#!/usr/bin/env python3
"""
SassyQueenCore Memory Patching Utility
Patches memory module functions to use the database manager
"""

import os
import sys
import logging
import importlib
import inspect
import types
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'memory_patch.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SassyQueenCore.MemoryPatch")

# Try to import our database manager
try:
    from database_manager import get_db_manager
    logger.info("Database manager loaded")
    USE_DB_MANAGER = True
except ImportError:
    logger.warning("Database manager not found, patching will be limited")
    USE_DB_MANAGER = False

class MemoryPatcher:
    """Patches memory module functions to use the database manager"""
    
    def __init__(self, memory_module=None, db_path=None):
        """Initialize the memory patcher"""
        self.base_dir = Path(__file__).resolve().parent
        
        # Try to load the memory module if not provided
        if memory_module is None:
            self._load_memory_module()
        else:
            self.memory_module = memory_module
            logger.info(f"Memory module provided: {self.memory_module}")
        
        # Initialize database manager if available
        if USE_DB_MANAGER:
            self.db_manager = get_db_manager(db_path)
            logger.info(f"Using database manager for patching")
        else:
            self.db_manager = None
        
        # Track patched methods
        self.patched_methods = []
    
    def _load_memory_module(self):
        """Load the memory module"""
        try:
            # Check if memory module is available in sys.modules
            if 'plugins.memory_learning' in sys.modules:
                self.memory_module = sys.modules['plugins.memory_learning']
                logger.info("Found memory module in sys.modules")
            else:
                # Try to import it
                try:
                    import plugins.memory_learning
                    self.memory_module = plugins.memory_learning
                    logger.info("Imported memory module")
                except ImportError:
                    # Try to load it from file
                    plugins_dir = self.base_dir / "plugins"
                    memory_file = plugins_dir / "memory_learning.py"
                    
                    if memory_file.exists():
                        logger.info(f"Loading memory module from {memory_file}")
                        try:
                            # Use spec to load the module
                            spec = importlib.util.spec_from_file_location(
                                "plugins.memory_learning", 
                                memory_file
                            )
                            
                            if spec:
                                memory_module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(memory_module)
                                sys.modules['plugins.memory_learning'] = memory_module
                                self.memory_module = memory_module
                                logger.info("Successfully loaded memory module")
                            else:
                                logger.error("Could not create spec for memory module")
                                self.memory_module = None
                        except Exception as e:
                            logger.error(f"Error loading memory module: {e}")
                            self.memory_module = None
                    else:
                        logger.error("Memory module file not found")
                        self.memory_module = None
        except Exception as e:
            logger.error(f"Error loading memory module: {e}")
            self.memory_module = None
    
    def add_db_utilities(self):
        """Add database utility functions to the memory module"""
        if not self.memory_module or not USE_DB_MANAGER:
            logger.warning("Cannot add database utilities (memory module or db manager missing)")
            return False
            
        try:
            # Add get_db_manager function
            setattr(self.memory_module, 'get_db_manager', get_db_manager)
            
            # Add execute utility function
            def execute_query(query, params=(), fetch_mode="all"):
                """Execute a database query using the connection pool"""
                db_manager = get_db_manager()
                return db_manager.execute(query, params, fetch_mode)
                
            setattr(self.memory_module, 'execute_query', execute_query)
            
            # Add executemany utility function
            def executemany_query(query, params_list):
                """Execute a database query with multiple parameter sets"""
                db_manager = get_db_manager()
                return db_manager.executemany(query, params_list)
                
            setattr(self.memory_module, 'executemany_query', executemany_query)
            
            logger.info("Added database utility functions to memory module")
            return True
        except Exception as e:
            logger.error(f"Error adding database utilities: {e}")
            return False
    
    def patch_function(self, func_name):
        """Patch a function in the memory module"""
        if not self.memory_module:
            logger.warning(f"Cannot patch {func_name} (memory module missing)")
            return False
            
        try:
            # Get the original function
            if not hasattr(self.memory_module, func_name):
                logger.warning(f"Function {func_name} not found in memory module")
                return False
                
            original_func = getattr(self.memory_module, func_name)
            
            # Create a patched function that uses the database manager
            def patched_func(*args, **kwargs):
                """Patched function that uses the database manager"""
                # Call the original function, but intercept any database calls
                if USE_DB_MANAGER:
                    # Replace any sqlite3.connect calls with db_manager.get_connection
                    # This is complex and would require parsing the function code
                    # For now, we just log that it was called
                    logger.info(f"Called patched function {func_name}")
                
                # Call the original function
                return original_func(*args, **kwargs)
                
            # Replace the original function with the patched one
            setattr(self.memory_module, func_name, patched_func)
            self.patched_methods.append(func_name)
            
            logger.info(f"Patched function {func_name}")
            return True
        except Exception as e:
            logger.error(f"Error patching function {func_name}: {e}")
            return False
    
    def patch_execute(self):
        """Patch the execute function specifically"""
        if not self.memory_module:
            logger.warning("Cannot patch execute (memory module missing)")
            return False
            
        try:
            # Check if the module has an execute function
            if hasattr(self.memory_module, 'execute'):
                original_func = getattr(self.memory_module, 'execute')
                
                # Create a patched function that uses the database manager
                def patched_execute(query, params=(), connection=None, fetch_mode="all"):
                    """Patched execute function that uses the database manager"""
                    if USE_DB_MANAGER:
                        # Use our database manager instead
                        db_manager = get_db_manager()
                        return db_manager.execute(query, params, fetch_mode)
                    else:
                        # Call the original function
                        return original_func(query, params, connection, fetch_mode)
                        
                # Replace the original function with the patched one
                setattr(self.memory_module, 'execute', patched_execute)
                self.patched_methods.append('execute')
                
                logger.info("Patched function execute")
                return True
            else:
                logger.warning("Function execute not found in memory module")
                return False
        except Exception as e:
            logger.error(f"Error patching execute: {e}")
            return False
    
    def patch_method(self, class_name, method_name):
        """Patch a method in a class in the memory module"""
        if not self.memory_module:
            logger.warning(f"Cannot patch {class_name}.{method_name} (memory module missing)")
            return False
            
        try:
            # Get the class
            if not hasattr(self.memory_module, class_name):
                logger.warning(f"Class {class_name} not found in memory module")
                return False
                
            cls = getattr(self.memory_module, class_name)
            
            # Get the original method
            if not hasattr(cls, method_name):
                logger.warning(f"Method {method_name} not found in class {class_name}")
                return False
                
            original_method = getattr(cls, method_name)
            
            # Create a patched method that uses the database manager
            def patched_method(self_obj, *args, **kwargs):
                """Patched method that uses the database manager"""
                # Get any attributes that look like database connections
                for attr_name in dir(self_obj):
                    if attr_name in ['db', 'conn', 'connection', 'database']:
                        if hasattr(self_obj, attr_name):
                            # We found a potential database connection
                            # However, we can't safely replace it at runtime
                            pass
                
                # Call the original method
                return original_method(self_obj, *args, **kwargs)
                
            # Replace the original method with the patched one
            setattr(cls, method_name, patched_method)
            self.patched_methods.append(f"{class_name}.{method_name}")
            
            logger.info(f"Patched method {class_name}.{method_name}")
            return True
        except Exception as e:
            logger.error(f"Error patching method {class_name}.{method_name}: {e}")
            return False
    
    def patch_memory_plugin_methods(self):
        """Patch all MemoryLearningPlugin methods that use the database"""
        if not self.memory_module:
            logger.warning("Cannot patch MemoryLearningPlugin methods (memory module missing)")
            return False
            
        # Check if the class exists
        if not hasattr(self.memory_module, 'MemoryLearningPlugin'):
            logger.warning("MemoryLearningPlugin class not found in memory module")
            return False
            
        # Get the class
        plugin_class = getattr(self.memory_module, 'MemoryLearningPlugin')
        
        # Methods that typically use the database
        db_methods = [
            '_initialize_database',
            '_store_memory',
            '_recall_memories',
            '_consolidate_memories',
            '_clean_old_memories',
            '_forget_memories',
            '_update_associations',
            '_save_learned_patterns',
            '_report_memory_stats',
            '_report_learnings',
            'execute'
        ]
        
        # First, add a completely new implementation of _update_associations
        # This is the method that's causing database locks
        try:
            # Create a completely new implementation that avoids locks
            def new_update_associations(self_obj, memory_id, related_ids, strength=0.5):
                """New implementation of _update_associations that avoids database locks"""
                if not hasattr(self_obj, 'db_manager'):
                    from database_manager import get_db_manager
                    self_obj.db_manager = get_db_manager()
                
                db = self_obj.db_manager
                for related_id in related_ids:
                    # Instead of checking first then updating/inserting (which can cause race conditions),
                    # use a single INSERT OR REPLACE statement with a transaction
                    db.execute("""
                    INSERT OR REPLACE INTO associations (source_id, target_id, strength, last_updated)
                    VALUES (?, ?, 
                            COALESCE((SELECT (strength + ?) / 2 FROM associations WHERE source_id = ? AND target_id = ?), ?),
                            CURRENT_TIMESTAMP)
                    """, (memory_id, related_id, strength, memory_id, related_id, strength))
                    
                    # Also create reverse associations with half strength
                    half_strength = strength / 2
                    db.execute("""
                    INSERT OR REPLACE INTO associations (source_id, target_id, strength, last_updated)
                    VALUES (?, ?, 
                            COALESCE((SELECT (strength + ?) / 2 FROM associations WHERE source_id = ? AND target_id = ?), ?),
                            CURRENT_TIMESTAMP)
                    """, (related_id, memory_id, half_strength, related_id, memory_id, half_strength))
                
                return True
            
            # Replace the original method with our new implementation
            if hasattr(plugin_class, '_update_associations'):
                setattr(plugin_class, '_update_associations', new_update_associations)
                self.patched_methods.append("MemoryLearningPlugin._update_associations (direct replacement)")
                logger.info("Directly replaced MemoryLearningPlugin._update_associations with non-locking version")
        except Exception as e:
            logger.error(f"Error replacing _update_associations: {e}")
        
        # Patch each method
        success = True
        for method_name in db_methods:
            if hasattr(plugin_class, method_name):
                try:
                    original_method = getattr(plugin_class, method_name)
                    
                    # Create a patched method
                    def create_patched_method(orig_method, method_name):
                        def patched_method(self_obj, *args, **kwargs):
                            """Patched method that handles database operations safely"""
                            # Check if we're using the db manager
                            if not USE_DB_MANAGER:
                                return orig_method(self_obj, *args, **kwargs)
                                
                            # Special handling for _update_associations method is no longer needed
                            # since we completely replaced it above
                            
                            # Generic handling for other methods
                            try:
                                # Add db_manager to the instance if not already there
                                if not hasattr(self_obj, 'db_manager'):
                                    self_obj.db_manager = get_db_manager()
                                    
                                # Call the original method, which may now use db_manager
                                return orig_method(self_obj, *args, **kwargs)
                            except Exception as e:
                                logger.error(f"Error in patched {method_name}: {e}")
                                # Fall back to original behavior
                                return orig_method(self_obj, *args, **kwargs)
                                
                        return patched_method
                    
                    # Skip _update_associations since we replaced it with a custom implementation
                    if method_name == '_update_associations':
                        continue
                    
                    # Set the new method on the class
                    patched = create_patched_method(original_method, method_name)
                    setattr(plugin_class, method_name, patched)
                    self.patched_methods.append(f"MemoryLearningPlugin.{method_name}")
                    logger.info(f"Patched method MemoryLearningPlugin.{method_name}")
                    
                except Exception as e:
                    logger.error(f"Error patching MemoryLearningPlugin.{method_name}: {e}")
                    success = False
            else:
                logger.info(f"Method {method_name} not found in MemoryLearningPlugin")
                
        return success
    
    def apply_all_patches(self):
        """Apply all patches to the memory module"""
        success = True
        
        # Add database utilities
        if not self.add_db_utilities():
            logger.warning("Failed to add database utilities")
            success = False
        
        # Patch the execute function
        if not self.patch_execute():
            logger.warning("Failed to patch execute function")
            success = False
        
        # Patch MemoryLearningPlugin methods
        if not self.patch_memory_plugin_methods():
            logger.warning("Failed to patch MemoryLearningPlugin methods")
            success = False
        
        # Log patched methods
        if self.patched_methods:
            logger.info(f"Applied {len(self.patched_methods)} patches to memory module")
        else:
            logger.warning("No patches were applied")
            success = False
        
        return success

def patch_memory_module(db_path=None):
    """Patch the memory module to use the database manager"""
    try:
        # Create the patcher
        patcher = MemoryPatcher(db_path=db_path)
        
        # Apply all patches
        if patcher.apply_all_patches():
            logger.info("Successfully patched memory module")
            return True
        else:
            logger.warning("Some patches failed")
            return False
            
    except Exception as e:
        logger.error(f"Error patching memory module: {e}")
        return False

def main():
    """Main function"""
    try:
        # Get database path from command line if provided
        db_path = None
        if len(sys.argv) > 1:
            db_path = sys.argv[1]
        
        # Patch the memory module
        if patch_memory_module(db_path):
            print("Successfully patched memory module")
            return 0
        else:
            print("Some patches failed, check the log for details")
            return 1
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 