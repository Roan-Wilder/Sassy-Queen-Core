@echo off
:: SassyQueenCore ROCm Installation Launcher
echo SassyQueenCore ROCm Installation Launcher
echo This script will help you install ROCm for your AMD RX590

:: Check for administrator privileges
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: This script requires administrator privileges.
    echo Please right-click and select "Run as administrator".
    goto END
)

:: Set base directory
set BASE_DIR=%~dp0
cd %BASE_DIR%

:: Set UTF-8 code page for Windows
chcp 65001 > nul
echo UTF-8 encoding enabled.

:: Install required packages
echo Installing required packages...
pip install wmi requests

:: Run the ROCm installation script
echo Running ROCm installation script...
python install_rocm.py

:END
echo.
echo Installation process completed.
pause 