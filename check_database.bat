@echo off
:: SassyQueenCore Database Lock Checker
echo SassyQueenCore Database Lock Checker

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

:: Check if memory database exists
echo Checking memory database status...
set "DB_FILE=%BASE_DIR%\memory_database.db"
if exist "%DB_FILE%" (
    echo Memory database found at: %DB_FILE%
    
    :: Try to access the database
    echo Testing database access...
    python -c "import sqlite3; try: conn = sqlite3.connect('%DB_FILE%', timeout=1); conn.execute('PRAGMA integrity_check'); conn.close(); print('Database is not locked and has integrity.'); except Exception as e: print('Database issue:', e)" 
    
    :: Check for WAL files
    echo Checking for WAL files...
    if exist "%DB_FILE%-wal" (
        echo WAL file found: %DB_FILE%-wal
    ) else (
        echo No WAL file found.
    )
    
    if exist "%DB_FILE%-shm" (
        echo SHM file found: %DB_FILE%-shm
    ) else (
        echo No SHM file found.
    )
    
    :: Get file details
    echo.
    echo Database file details:
    dir "%DB_FILE%*" /A
) else (
    echo Memory database not found at: %DB_FILE%
    echo Will be created by the system when needed.
)

:: Check if memory_learning.py exists
echo.
echo Checking memory module...
set "MEMORY_MODULE=%BASE_DIR%\plugins\memory_learning.py"
set "ACTIVE_MEMORY_MODULE=%BASE_DIR%\plugins\active\memory_learning.py"

if exist "%MEMORY_MODULE%" (
    echo Memory module found at: %MEMORY_MODULE%
) else (
    echo Memory module not found at: %MEMORY_MODULE%
)

if exist "%ACTIVE_MEMORY_MODULE%" (
    echo Active memory module found at: %ACTIVE_MEMORY_MODULE%
) else (
    echo Active memory module not found at: %ACTIVE_MEMORY_MODULE%
)

:: Check for our patch files
echo.
echo Checking patch files...
if exist "database_manager.py" (
    echo Database manager found.
) else (
    echo Database manager not found.
)

if exist "memory_db_patch.py" (
    echo Memory database patch found.
) else (
    echo Memory database patch not found.
)

if exist "memory_association_fix.py" (
    echo Memory association fix found.
) else (
    echo Memory association fix not found.
)

if exist "direct_run.py" (
    echo Direct run script found.
) else (
    echo Direct run script not found.
)

:: Create a Python script to report more database info
echo.
echo Creating detailed database report...
echo import os, sys, sqlite3, time > db_check.py
echo try: >> db_check.py
echo     print("Python version:", sys.version) >> db_check.py
echo     print("SQLite version:", sqlite3.sqlite_version) >> db_check.py
echo     db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_database.db") >> db_check.py
echo     print("Database path:", db_path) >> db_check.py
echo     if os.path.exists(db_path): >> db_check.py
echo         print("Database file size:", os.path.getsize(db_path), "bytes") >> db_check.py
echo         print("Last modified:", time.ctime(os.path.getmtime(db_path))) >> db_check.py
echo         try: >> db_check.py
echo             conn = sqlite3.connect(db_path, timeout=5) >> db_check.py
echo             cursor = conn.cursor() >> db_check.py
echo             cursor.execute("PRAGMA journal_mode") >> db_check.py
echo             print("Journal mode:", cursor.fetchone()[0]) >> db_check.py
echo             cursor.execute("PRAGMA busy_timeout") >> db_check.py
echo             print("Busy timeout:", cursor.fetchone()[0], "ms") >> db_check.py
echo             cursor.execute("SELECT name FROM sqlite_master WHERE type='table'") >> db_check.py
echo             tables = cursor.fetchall() >> db_check.py
echo             print("Tables in database:", len(tables)) >> db_check.py
echo             print("Table names:", [t[0] for t in tables]) >> db_check.py
echo             conn.close() >> db_check.py
echo             print("Successfully connected to and read from database.") >> db_check.py
echo         except Exception as e: >> db_check.py
echo             print("Error accessing database:", str(e)) >> db_check.py
echo     else: >> db_check.py
echo         print("Database file does not exist.") >> db_check.py
echo except Exception as e: >> db_check.py
echo     print("Error during check:", str(e)) >> db_check.py

python db_check.py
del db_check.py

:END
echo.
echo Database check completed.
pause 