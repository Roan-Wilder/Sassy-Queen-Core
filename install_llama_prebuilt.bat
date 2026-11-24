@echo off
:: Install pre-built llama-cpp-python
:: This tries multiple sources to find a working version
cd /d "%~dp0"

echo ========================================
echo Installing Pre-built llama-cpp-python
echo ========================================
echo.

echo Python version:
python --version
echo.

echo Step 1: Uninstalling any existing version...
python -m pip uninstall llama-cpp-python llama_cpp_python -y 2>nul

echo.
echo Step 2: Trying to install from PyPI...
python -m pip install llama-cpp-python --no-cache-dir

echo.
echo Step 3: Testing import...
python -c "from llama_cpp import Llama; print('SUCCESS!')"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo Standard install failed.
    echo Trying alternative: llama-cpp-python-cuda
    echo ========================================
    python -m pip uninstall llama-cpp-python -y 2>nul
    
    :: Try the CUDA version which sometimes has better compatibility
    python -m pip install llama-cpp-python-cuda --no-cache-dir
    
    python -c "from llama_cpp import Llama; print('SUCCESS with CUDA version!')"
    
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo ========================================
        echo STILL FAILING
        echo ========================================
        echo.
        echo The issue is likely Python 3.13 incompatibility.
        echo.
        echo RECOMMENDED: Install Python 3.11 from:
        echo https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
        echo.
        echo Then create a virtual environment:
        echo   "C:\Python311\python.exe" -m venv venv311
        echo   venv311\Scripts\activate
        echo   pip install llama-cpp-python PyQt6 transformers torch
        echo.
    )
)

echo.
pause
