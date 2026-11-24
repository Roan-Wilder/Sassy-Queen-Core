@echo off
:: SassyQueenCore Debug Script
echo SassyQueenCore Debug Mode

:: Set base directory
set BASE_DIR=%~dp0
cd %BASE_DIR%

:: Set UTF-8 code page for Windows
chcp 65001 > nul
echo UTF-8 encoding enabled.

:: Create necessary directories
echo Creating directories...
mkdir plugins\active 2>nul
mkdir config 2>nul
mkdir logs 2>nul
mkdir learning_data 2>nul

:: Check Python installation
echo Checking Python installation...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found or not in PATH.
    goto END
)

:: Check PyQt6 installation
echo Checking PyQt6 installation...
python -c "import PyQt6" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo PyQt6 not installed. Attempting to install...
    python -m pip install PyQt6
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to install PyQt6.
        goto END
    )
)

:: Create Python package files
echo Creating Python package files...
echo. > plugins\__init__.py
echo. > plugins\active\__init__.py

:: Fix memory plugin
echo Checking memory plugin...
if exist plugins\memory_learning.py (
    echo Moving memory_learning.py to active plugins directory...
    copy plugins\memory_learning.py plugins\active\ /Y
    echo Plugin moved successfully.
) else if not exist plugins\active\memory_learning.py (
    echo WARNING: memory_learning.py not found in plugins or plugins\active directory.
)

:: Check for necessary files
echo Checking for necessary files...
if not exist scripts\sassy_gui.py (
    echo ERROR: sassy_gui.py not found in scripts directory.
    goto END
)

if not exist scripts\system_integration.py (
    echo ERROR: system_integration.py not found in scripts directory.
    goto END
)

:: Set PYTHONPATH to include current directory
echo Setting PYTHONPATH...
set PYTHONPATH=%BASE_DIR%;%PYTHONPATH%

:: Set Python UTF-8 mode (Python 3.7+)
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: Run with debug output and encoding fixes
echo Running SassyQueenCore with debug output...
python -X utf8 -c "import io, sys; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'); sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace'); import scripts.sassy_gui; scripts.sassy_gui.main()"

:END
echo Debug completed.
pause 