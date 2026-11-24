#!/usr/bin/env python3
"""
SassyQueenCore GUI Launcher
This script launches the GUI interface with proper path handling
"""

import os
import sys
import importlib.util
from pathlib import Path
import traceback
import io

def import_or_install(package_name):
    """Import a package, or install it if not available"""
    try:
        return importlib.import_module(package_name)
    except ImportError:
        import subprocess
        print(f"{package_name} not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return importlib.import_module(package_name)

def setup_environment():
    """Set up the environment for running the GUI"""
    # Get the base directory
    script_path = Path(__file__).resolve()
    base_dir = script_path.parent.parent
    
    # Add base directory to Python path
    sys.path.insert(0, str(base_dir))
    
    # Create necessary directories
    (base_dir / "plugins" / "active").mkdir(exist_ok=True, parents=True)
    (base_dir / "config").mkdir(exist_ok=True)
    (base_dir / "logs").mkdir(exist_ok=True)
    (base_dir / "learning_data").mkdir(exist_ok=True)
    
    # Create __init__.py files to make directories packages
    (base_dir / "plugins" / "__init__.py").touch(exist_ok=True)
    (base_dir / "plugins" / "active" / "__init__.py").touch(exist_ok=True)
    
    # Fix system encoding to handle non-standard characters
    if sys.platform == 'win32':
        # Force UTF-8 encoding on Windows
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    
    # Check if PyQt6 is installed
    try:
        import_or_install("PyQt6")
    except Exception as e:
        print(f"Error installing PyQt6: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Copy memory_learning.py to active plugins if it exists in the plugins root
    memory_plugin_src = base_dir / "plugins" / "memory_learning.py"
    memory_plugin_dst = base_dir / "plugins" / "active" / "memory_learning.py"
    
    if memory_plugin_src.exists() and not memory_plugin_dst.exists():
        print("Copying memory_learning.py to active plugins directory...")
        try:
            # Use explicit UTF-8 encoding with error handling
            with open(memory_plugin_src, 'r', encoding='utf-8', errors='replace') as src_file:
                content = src_file.read()
                
            with open(memory_plugin_dst, 'w', encoding='utf-8') as dst_file:
                dst_file.write(content)
        except Exception as e:
            print(f"Warning: Error copying plugin file: {e}")
            # Try alternative copy method
            import shutil
            try:
                shutil.copy2(memory_plugin_src, memory_plugin_dst)
                print("Used alternative copy method successfully.")
            except Exception as e2:
                print(f"Error with alternative copy: {e2}")
    
    return base_dir

def run_gui():
    """Run the SassyQueenCore GUI"""
    try:
        base_dir = setup_environment()
        print("Environment set up successfully.")
        
        # Now try to import and run the GUI
        script_path = base_dir / "scripts" / "sassy_gui.py"
        
        if not script_path.exists():
            print(f"Error: {script_path} not found.")
            input("Press Enter to exit...")
            return
        
        print("Launching SassyQueenCore GUI...")
        
        # Add the scripts directory to the path
        sys.path.insert(0, str(base_dir / "scripts"))
        
        # Set default encoding for all file operations
        import codecs
        codecs.register_error('strict', codecs.replace_errors)
        
        # Load the sassy_gui module
        spec = importlib.util.spec_from_file_location("sassy_gui", script_path)
        if spec is None:
            print("Error: Could not load sassy_gui.py")
            input("Press Enter to exit...")
            return
            
        sassy_gui = importlib.util.module_from_spec(spec)
        sys.modules["sassy_gui"] = sassy_gui
        
        # Execute module with error handling
        try:
            spec.loader.exec_module(sassy_gui)
        except UnicodeDecodeError as ude:
            print(f"Unicode decode error: {ude}")
            print("This is likely due to a character encoding issue in one of the files.")
            print("Try running with the debug_sassy.bat script instead.")
            input("Press Enter to exit...")
            return
            
        # Run the main function
        sassy_gui.main()
        
    except Exception as e:
        print(f"Error launching GUI: {e}")
        print("\nTraceback:")
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    # Set default encoding to UTF-8
    if sys.platform == 'win32':
        # Force UTF-8 as default encoding on Windows
        import locale
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        
    run_gui() 