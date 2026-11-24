@echo off
:: SassyQueenCore Direct Runner with Enhanced Database Handling
echo SassyQueenCore Direct Runner with Enhanced Database Handling

:: Set base directory to script location
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

:: Set UTF-8 code page for Windows
chcp 65001 > nul
echo UTF-8 encoding enabled.

:: Set Python environment variables for UTF-8
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: Enable delayed expansion for variables
setlocal EnableDelayedExpansion

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

:: Fix hanging connections first
echo.
echo Detecting and fixing hanging connections...
if exist "hanging_connections.py" (
    python -X utf8 hanging_connections.py
) else (
    echo WARNING: hanging_connections.py not found, skipping this step.
)

:: Forcefully terminate any Python processes that might lock the database
echo.
echo Terminating Python processes...
taskkill /F /FI "IMAGENAME eq python.exe" >nul 2>&1
timeout /t 2 >nul

:: Delete any lock files that might exist
echo Checking for lock files...
if exist "memory_database.db-journal" del "memory_database.db-journal"
if exist "memory_database.db-wal" del "memory_database.db-wal"
if exist "memory_database.db-shm" del "memory_database.db-shm"
if exist "memory_database.db.lock" del "memory_database.db.lock"

:: Check if database needs rebuilding
echo.
echo Checking database integrity...
python -X utf8 -c "import sqlite3; conn=None; try: conn=sqlite3.connect('memory_database.db', timeout=1); cursor=conn.cursor(); cursor.execute('PRAGMA integrity_check'); result=cursor.fetchone()[0]; conn.close(); print(f'Database integrity: {result}'); exit(0 if result=='ok' else 1); except Exception as e: print(f'Database check failed: {e}'); exit(1)" >nul 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Database integrity check failed.
    
    echo.
    echo Do you want to rebuild the database from scratch? (y/n)
    set /p REBUILD_CHOICE="> "
    if /i "!REBUILD_CHOICE!"=="y" (
        if exist "db_rebuild.py" (
            echo.
            echo Running database rebuild utility...
            python -X utf8 db_rebuild.py --auto
        ) else (
            echo ERROR: db_rebuild.py not found.
        )
    )
)

:: Run DB unlock utility with automatic and force options
echo.
echo Running database unlock utility...
if exist "db_unlock.py" (
    python -X utf8 db_unlock.py --force --auto
    if %ERRORLEVEL% NEQ 0 (
        echo WARNING: Database unlock utility encountered errors. Will try to continue.
    )
)

:: Initialize database lock monitor instead of the old controller
echo Starting database lock monitor...
if exist "db_lock_manager.py" (
    start /b python -X utf8 db_lock_manager.py
    echo Database lock monitor started in background
) else (
    echo WARNING: db_lock_manager.py not found!
    
    :: Fall back to old lock controller if available
    if exist "db_lock_controller.py" (
        python -X utf8 -c "import db_lock_controller"
        echo Using older db_lock_controller as fallback
    ) else (
        echo ERROR: No database lock management available!
        echo This may cause database locking issues.
    )
)

:: Apply sqlite3 connection patches using the dedicated patcher script
echo Patching sqlite3 connections...
if exist "sqlite3_patcher.py" (
    python -X utf8 sqlite3_patcher.py
) else (
    echo ERROR: sqlite3_patcher.py not found!
    echo This may cause database locking issues.
)

:: Apply memory patches
echo Applying memory database patches...
if exist "memory_db_patch.py" (
    python -X utf8 memory_db_patch.py
)

:: Apply memory association fix with improved handling
echo Applying memory association patches...
if exist "memory_association_fix.py" (
    python -X utf8 memory_association_fix.py
    if %ERRORLEVEL% NEQ 0 (
        echo WARNING: Memory association fix encountered errors. Will try to continue.
    )
)

:: Run the direct launcher
echo Running direct launcher...
python -X utf8 direct_run.py

:: Cleanup - terminate the background lock monitor when the application exits
echo.
echo Cleaning up...
taskkill /F /FI "WINDOWTITLE eq Database lock monitor running*" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Database lock monitor running*" >nul 2>&1

:END
echo.
echo SassyQueenCore session ended.
pause 