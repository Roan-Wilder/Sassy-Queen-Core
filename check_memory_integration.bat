@echo off
:: SassyQueenCore Memory Capabilities Bridge Check
echo SassyQueenCore Memory Integration Check

:: Set base directory to script location
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

:: Set UTF-8 code page for Windows
chcp 65001 > nul
echo UTF-8 encoding enabled.

:: Set Python environment variables for UTF-8
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: Check Python installation
echo Checking Python installation...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found or not in PATH.
    goto END
)

:: Run the memory capabilities bridge
echo Checking memory integration with capabilities and modes...
python -X utf8 memory_capabilities_bridge.py

:END
echo.
echo Memory integration check completed.
pause 