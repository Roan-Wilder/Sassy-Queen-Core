@echo off
:: SassyQueenCore Database Reset
echo SassyQueenCore Database Reset
echo -----------------------------

:: Set base directory to script location
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

:: Check Python installation
echo Checking Python installation...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found or not in PATH.
    goto END
)

:: Kill any running Python processes
echo.
echo Terminating Python processes...
taskkill /F /FI "IMAGENAME eq python.exe" >nul 2>&1
timeout /t 2 >nul

:: Run the reset script
echo.
echo Running database reset script...
python reset_db.py

echo.
echo If reset was successful, you can now run SassyQueenCore with run_direct.bat

:END
echo.
pause 