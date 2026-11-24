#!/usr/bin/env python3
"""
SassyQueenCore Simple Launcher
A simplified launcher that fixes import issues on the fly
"""

import os
import sys
import io
import importlib.util
from pathlib import Path
import traceback

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')

def run_sassyqueencore():
    """Set up environment and run SassyQueenCore"""
    try:
        # Get base directory
        base_dir = Path(__file__).resolve().parent
        print(f"Base directory: {base_dir}")
        
        # Add base directory to path
        sys.path.insert(0, str(base_dir))
        
        # Create necessary directories
        plugins_dir = base_dir / "plugins"
        active_dir = plugins_dir / "active"
        config_dir = base_dir / "config"
        logs_dir = base_dir / "logs"
        learning_dir = base_dir / "learning_data"
        
        for directory in [plugins_dir, active_dir, config_dir, logs_dir, learning_dir]:
            directory.mkdir(exist_ok=True)
        
        # Create package __init__ files
        for init_file in [plugins_dir / "__init__.py", active_dir / "__init__.py"]:
            if not init_file.exists():
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write("# Package initialization\n")
        
        # Find and copy memory_learning.py
        memory_file = None
        for location in [
            plugins_dir / "memory_learning.py",
            active_dir / "memory_learning.py",
            base_dir / "memory_learning.py"
        ]:
            if location.exists():
                memory_file = location
                print(f"Found memory_learning.py at: {location}")
                break
        
        if memory_file:
            # Make sure it's in both locations
            import shutil
            if memory_file != active_dir / "memory_learning.py":
                print(f"Copying to active plugins: {active_dir}")
                shutil.copy2(memory_file, active_dir / "memory_learning.py")
            
            if memory_file != plugins_dir / "memory_learning.py":
                print(f"Copying to plugins directory: {plugins_dir}")
                shutil.copy2(memory_file, plugins_dir / "memory_learning.py")
        else:
            print("WARNING: memory_learning.py not found!")
        
        # Manually load the memory_learning module
        try:
            print("Manually loading memory_learning module...")
            memory_module_path = active_dir / "memory_learning.py"
            if memory_module_path.exists():
                spec = importlib.util.spec_from_file_location(
                    "plugins.active.memory_learning", 
                    memory_module_path
                )
                memory_module = importlib.util.module_from_spec(spec)
                sys.modules["plugins.active.memory_learning"] = memory_module
                spec.loader.exec_module(memory_module)
                print("Memory module loaded successfully")
            
                # Also make it available at plugins.memory_learning
                sys.modules["plugins.memory_learning"] = memory_module
        except Exception as e:
            print(f"Warning: Could not pre-load memory module: {e}")
        
        # Check for PyQt6
        try:
            import PyQt6
            print("PyQt6 is already installed")
        except ImportError:
            print("PyQt6 not found. Installing...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])
            import PyQt6
        
        # Add scripts directory to path
        scripts_dir = base_dir / "scripts"
        sys.path.insert(0, str(scripts_dir))
        
        # Try to import and run the GUI
        try:
            print("Importing sassy_gui module...")
            spec = importlib.util.spec_from_file_location(
                "sassy_gui", 
                scripts_dir / "sassy_gui.py"
            )
            if spec is None:
                print("Error: Could not find sassy_gui.py")
                return
            
            sassy_gui = importlib.util.module_from_spec(spec)
            sys.modules["sassy_gui"] = sassy_gui
            spec.loader.exec_module(sassy_gui)
            
            print("Launching SassyQueenCore GUI...")
            sassy_gui.main()
        except Exception as e:
            print(f"Error running GUI: {e}")
            traceback.print_exc()
    
    except Exception as e:
        print(f"Startup error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_sassyqueencore()
    input("Press Enter to exit...") 