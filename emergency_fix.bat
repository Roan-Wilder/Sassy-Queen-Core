@echo off
:: SassyQueenCore Emergency Fix for Module Import Error
echo SassyQueenCore Emergency Fix

:: Set base directory
set BASE_DIR=%~dp0
cd %BASE_DIR%

:: Set UTF-8 code page for Windows
chcp 65001 > nul
echo UTF-8 encoding enabled.

:: Create the emergency fix script
echo import os, sys, shutil > emergency.py
echo from pathlib import Path >> emergency.py
echo. >> emergency.py
echo # Get base directory >> emergency.py
echo base_dir = Path(r"%BASE_DIR%").resolve() >> emergency.py
echo print(f"Base directory: {base_dir}") >> emergency.py
echo. >> emergency.py
echo # Create directories >> emergency.py
echo plugins_dir = base_dir / "plugins" >> emergency.py
echo active_dir = plugins_dir / "active" >> emergency.py
echo plugins_dir.mkdir(exist_ok=True) >> emergency.py
echo active_dir.mkdir(exist_ok=True) >> emergency.py
echo. >> emergency.py
echo # Create __init__.py files >> emergency.py
echo with open(plugins_dir / "__init__.py", "w") as f: >> emergency.py
echo     f.write("# Plugins package\n") >> emergency.py
echo with open(active_dir / "__init__.py", "w") as f: >> emergency.py
echo     f.write("# Active plugins package\n") >> emergency.py
echo. >> emergency.py
echo # Find memory_learning.py >> emergency.py
echo memory_file = None >> emergency.py
echo for location in [ >> emergency.py
echo     plugins_dir / "memory_learning.py", >> emergency.py
echo     active_dir / "memory_learning.py", >> emergency.py
echo     base_dir / "memory_learning.py" >> emergency.py
echo ]: >> emergency.py
echo     if location.exists(): >> emergency.py
echo         memory_file = location >> emergency.py
echo         print(f"Found memory_learning.py at: {location}") >> emergency.py
echo         break >> emergency.py
echo. >> emergency.py
echo if memory_file: >> emergency.py
echo     # Copy to both locations >> emergency.py
echo     print("Copying memory_learning.py to plugins directories") >> emergency.py
echo     if str(memory_file) != str(plugins_dir / "memory_learning.py"): >> emergency.py
echo         shutil.copy2(memory_file, plugins_dir / "memory_learning.py") >> emergency.py
echo     if str(memory_file) != str(active_dir / "memory_learning.py"): >> emergency.py
echo         shutil.copy2(memory_file, active_dir / "memory_learning.py") >> emergency.py
echo     print("Done!") >> emergency.py
echo else: >> emergency.py
echo     print("ERROR: memory_learning.py not found!") >> emergency.py
echo. >> emergency.py
echo input("Press Enter to exit...") >> emergency.py

:: Run the emergency fix
echo Running emergency fix...
python emergency.py

:: Clean up
if exist emergency.py del emergency.py

echo.
echo Emergency fix completed. Try running SassyQueenCore again.
pause 