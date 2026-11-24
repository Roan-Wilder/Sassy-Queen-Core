@echo off
:: SassyQueenCore Database Rebuilder
echo SassyQueenCore Database Rebuilder
echo ---------------------------------

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

:: Install required dependencies if needed
echo Checking dependencies...
python -c "import psutil" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing psutil...
    python -m pip install psutil
)

:: Terminate any Python processes that might lock the database
echo.
echo Terminating Python processes...
taskkill /F /FI "IMAGENAME eq python.exe" >nul 2>&1
timeout /t 2 >nul

:: Run hanging connections detector
echo.
echo Detecting and fixing hanging connections...
if exist "hanging_connections.py" (
    python -X utf8 hanging_connections.py
) else (
    echo WARNING: hanging_connections.py not found, skipping this step.
)

:: Ask for rebuild type
echo.
echo Database Rebuild Options:
echo 1. Standard rebuild (preserve data if possible)
echo 2. Clean rebuild (empty database)
echo 3. Force rebuild (try to preserve data, but continue even if errors occur)
echo.
set /p REBUILD_TYPE=Enter your choice (1-3) [default=1]: 

:: Set default if empty
if "%REBUILD_TYPE%"=="" set REBUILD_TYPE=1

:: Run the appropriate rebuild
echo.
echo Running database rebuild...
if "%REBUILD_TYPE%"=="1" (
    python -X utf8 db_rebuild.py
) else if "%REBUILD_TYPE%"=="2" (
    python -X utf8 db_rebuild.py --empty
) else if "%REBUILD_TYPE%"=="3" (
    python -X utf8 db_rebuild.py --force
) else (
    echo Invalid choice. Using standard rebuild.
    python -X utf8 db_rebuild.py
)

:: Run DB unlock utility after rebuild
echo.
echo Running database unlock utility...
if exist "db_unlock.py" (
    python -X utf8 db_unlock.py --force --auto
)

echo.
echo Database rebuild process completed.
echo You can now run SassyQueenCore with run_direct.bat

:END
echo.
pause 