@echo off
:: Script to fix plugin directory structure

echo Setting up plugin directory structure...

:: Create necessary directories
if not exist plugins\active mkdir plugins\active
if not exist plugins\config mkdir plugins\config
if not exist plugins\disabled mkdir plugins\disabled

:: Create __init__.py files to make directories Python packages
echo. > plugins\__init__.py
echo. > plugins\active\__init__.py

:: Copy memory_learning.py to the active plugins directory if it exists
if exist plugins\memory_learning.py (
    echo Moving memory_learning.py to active plugins directory...
    copy plugins\memory_learning.py plugins\active\
    echo Plugin moved successfully.
) else (
    echo memory_learning.py not found in plugins directory.
)

echo Plugin structure setup complete.
pause 