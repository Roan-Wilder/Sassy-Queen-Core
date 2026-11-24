@echo off
:: SassyQueenCore Encoding Fix Script
echo SassyQueenCore Encoding Fix

:: Set base directory
set BASE_DIR=%~dp0
cd %BASE_DIR%

:: Set UTF-8 code page for Windows
chcp 65001 > nul
echo UTF-8 encoding enabled.

echo.
echo This script will fix character encoding issues in SassyQueenCore files.
echo.

:: Check Python installation
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found or not in PATH.
    goto END
)

:: Run the encoding fix script
echo Creating Python encoding fix script...
echo import os, sys, codecs, glob > fix_encoding.py
echo from pathlib import Path >> fix_encoding.py
echo. >> fix_encoding.py
echo def fix_file(filepath): >> fix_encoding.py
echo     print(f"Checking {filepath}...") >> fix_encoding.py
echo     try: >> fix_encoding.py
echo         with open(filepath, 'rb') as f: >> fix_encoding.py
echo             content = f.read() >> fix_encoding.py
echo         # Try to decode with different encodings >> fix_encoding.py
echo         for encoding in ['utf-8', 'latin-1', 'cp1252']: >> fix_encoding.py
echo             try: >> fix_encoding.py
echo                 decoded = content.decode(encoding, errors='strict') >> fix_encoding.py
echo                 print(f"  - Successfully decoded with {encoding}") >> fix_encoding.py
echo                 # Write back with UTF-8 encoding >> fix_encoding.py
echo                 with open(filepath, 'w', encoding='utf-8') as f: >> fix_encoding.py
echo                     f.write(decoded) >> fix_encoding.py
echo                 print(f"  - Converted to UTF-8") >> fix_encoding.py
echo                 return True >> fix_encoding.py
echo             except UnicodeDecodeError: >> fix_encoding.py
echo                 continue >> fix_encoding.py
echo         # If all encodings fail, use errors='replace' >> fix_encoding.py
echo         print(f"  - Could not determine encoding, using replacement mode") >> fix_encoding.py
echo         decoded = content.decode('utf-8', errors='replace') >> fix_encoding.py
echo         with open(filepath, 'w', encoding='utf-8') as f: >> fix_encoding.py
echo             f.write(decoded) >> fix_encoding.py
echo         return True >> fix_encoding.py
echo     except Exception as e: >> fix_encoding.py
echo         print(f"  - Error processing file: {e}") >> fix_encoding.py
echo         return False >> fix_encoding.py
echo. >> fix_encoding.py
echo base_dir = Path('%BASE_DIR%').resolve() >> fix_encoding.py
echo. >> fix_encoding.py
echo # Find all Python files >> fix_encoding.py
echo python_files = [] >> fix_encoding.py
echo for ext in ['.py', '.json']: >> fix_encoding.py
echo     python_files.extend(list(base_dir.glob(f"**/*{ext}"))) >> fix_encoding.py
echo. >> fix_encoding.py
echo print(f"Found {len(python_files)} files to check") >> fix_encoding.py
echo fixed_count = 0 >> fix_encoding.py
echo. >> fix_encoding.py
echo for file in python_files: >> fix_encoding.py
echo     if fix_file(file): >> fix_encoding.py
echo         fixed_count += 1 >> fix_encoding.py
echo. >> fix_encoding.py
echo print(f"Processed {fixed_count} files") >> fix_encoding.py
echo print("Encoding fix complete.") >> fix_encoding.py

echo Running fix script...
python fix_encoding.py

echo.
echo Cleaning up...
if exist fix_encoding.py del fix_encoding.py

:END
echo.
echo Encoding fix completed. Try running SassyQueenCore again.
pause 