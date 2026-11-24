#!/usr/bin/env python3
"""
SassyQueenCore Plugin Fix Script
This script fixes the plugin structure and import issues
"""

import os
import sys
import shutil
from pathlib import Path

def fix_plugins():
    """Fix the plugin structure and import issues"""
    # Get the base directory
    base_dir = Path(__file__).resolve().parent
    print(f"Base directory: {base_dir}")
    
    # Create necessary directories
    plugins_dir = base_dir / "plugins"
    active_dir = plugins_dir / "active"
    
    plugins_dir.mkdir(exist_ok=True)
    active_dir.mkdir(exist_ok=True)
    
    # Create __init__.py files
    init_file1 = plugins_dir / "__init__.py"
    init_file2 = active_dir / "__init__.py"
    
    if not init_file1.exists():
        with open(init_file1, 'w', encoding='utf-8') as f:
            f.write("# Plugins package\n")
    
    if not init_file2.exists():
        with open(init_file2, 'w', encoding='utf-8') as f:
            f.write("# Active plugins package\n")
    
    # Check for memory_learning.py in various locations
    possible_locations = [
        plugins_dir / "memory_learning.py",
        active_dir / "memory_learning.py",
        base_dir / "memory_learning.py",
    ]
    
    source_file = None
    for loc in possible_locations:
        if loc.exists():
            source_file = loc
            print(f"Found memory_learning.py at: {loc}")
            break
    
    if source_file is None:
        print("ERROR: memory_learning.py not found!")
        return False
    
    # Copy to active plugins if needed
    if source_file != active_dir / "memory_learning.py":
        print(f"Copying memory_learning.py to {active_dir}")
        try:
            shutil.copy2(source_file, active_dir / "memory_learning.py")
        except Exception as e:
            print(f"Error copying file: {e}")
            return False
    
    # Fix imports in system_integration.py
    system_integration = base_dir / "scripts" / "system_integration.py"
    if system_integration.exists():
        print("Fixing imports in system_integration.py")
        try:
            with open(system_integration, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Fix import statements
            if "from plugins.memory_learning import" in content:
                content = content.replace(
                    "from plugins.memory_learning import", 
                    "from plugins.active.memory_learning import"
                )
            
            if "from plugins.active.active.memory_learning import" in content:
                content = content.replace(
                    "from plugins.active.active.memory_learning import", 
                    "from plugins.active.memory_learning import"
                )
            
            with open(system_integration, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            print(f"Error fixing imports: {e}")
            return False
    
    # Fix imports in sassy_gui.py
    sassy_gui = base_dir / "scripts" / "sassy_gui.py"
    if sassy_gui.exists():
        print("Fixing imports in sassy_gui.py")
        try:
            with open(sassy_gui, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Fix import statements
            if "from plugins.memory_learning import" in content:
                content = content.replace(
                    "from plugins.memory_learning import", 
                    "from plugins.active.memory_learning import"
                )
            
            if "from plugins.active.active.memory_learning import" in content:
                content = content.replace(
                    "from plugins.active.active.memory_learning import", 
                    "from plugins.active.memory_learning import"
                )
            
            with open(sassy_gui, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            print(f"Error fixing imports: {e}")
            return False
    
    # Create symbolic links to help with imports
    try:
        memory_learning_src = active_dir / "memory_learning.py"
        memory_learning_dst = plugins_dir / "memory_learning.py"
        
        if memory_learning_src.exists() and not memory_learning_dst.exists():
            print("Creating symbolic link for memory_learning.py")
            try:
                # Try to create a symlink (Windows requires admin privileges)
                os.symlink(memory_learning_src, memory_learning_dst)
            except:
                # Fall back to copying the file
                shutil.copy2(memory_learning_src, memory_learning_dst)
    except Exception as e:
        print(f"Warning: {e}")
    
    print("Plugin structure fixed successfully!")
    return True

if __name__ == "__main__":
    try:
        if fix_plugins():
            print("Plugins fixed successfully. You can now run SassyQueenCore.")
        else:
            print("Failed to fix plugins. Check errors above.")
            
        input("Press Enter to exit...")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...") 