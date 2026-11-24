@echo off
:: Fix llama-cpp-python for Python 3.13
cd /d "%~dp0"

echo ========================================
echo Fixing llama-cpp-python Installation
echo ========================================
echo.

:: Show Python version
echo Checking Python version...
python --version
echo.

:: Check if it's Python 3.13
python -c "import sys; v=sys.version_info; exit(0 if v.major==3 and v.minor==13 else 1)"
if %ERRORLEVEL% EQU 0 (
    echo WARNING: Python 3.13 detected!
    echo llama-cpp-python may not have pre-built wheels for Python 3.13.
    echo.
    echo Options:
    echo 1. Try installing from a specific wheel URL
    echo 2. Build from source (requires Visual Studio Build Tools)
    echo 3. Use Python 3.11 or 3.12 instead
    echo.
)

echo.
echo Step 1: Uninstalling existing llama-cpp-python...
python -m pip uninstall llama-cpp-python -y

echo.
echo Step 2: Installing Visual C++ Build Tools dependencies...
python -m pip install cmake setuptools wheel

echo.
echo Step 3: Trying to install llama-cpp-python...
echo This may take several minutes if building from source...
python -m pip install llama-cpp-python --no-cache-dir --verbose

echo.
echo Step 4: Testing installation...
python -c "from llama_cpp import Llama; print('SUCCESS: llama-cpp-python is working!')"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo FAILED: llama-cpp-python installation is broken.
    echo.
    echo RECOMMENDED FIX:
    echo Install Python 3.11 or 3.12 alongside 3.13, then use that version.
    echo Download from: https://www.python.org/downloads/
    echo.
)

echo.
pause
