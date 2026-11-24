# SassyQueenCore PowerShell Fix and Run Script
Write-Host "SassyQueenCore PowerShell Fix and Run" -ForegroundColor Cyan

# Set working directory to script location
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Create Python script content
$pythonScript = @"
import os
import sys
import io
import shutil
from pathlib import Path
import importlib.util
import traceback

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')

def main():
    try:
        # Get current directory
        current_dir = Path(os.getcwd())
        print(f"Working in: {current_dir}")
        
        # Add to path
        sys.path.insert(0, str(current_dir))
        
        # Create directories
        plugins_dir = current_dir / "plugins"
        active_dir = plugins_dir / "active"
        config_dir = current_dir / "config"
        logs_dir = current_dir / "logs"
        learning_dir = current_dir / "learning_data"
        
        for directory in [plugins_dir, active_dir, config_dir, logs_dir, learning_dir]:
            directory.mkdir(exist_ok=True)
            print(f"Created directory: {directory}")
        
        # Create __init__.py files
        for init_file in [plugins_dir / "__init__.py", active_dir / "__init__.py"]:
            if not init_file.exists():
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write("# Package initialization\\n")
                print(f"Created: {init_file}")
        
        # Find memory_learning.py
        memory_file = None
        for location in [
            plugins_dir / "memory_learning.py",
            active_dir / "memory_learning.py",
            current_dir / "memory_learning.py"
        ]:
            if location.exists():
                memory_file = location
                print(f"Found memory_learning.py at: {location}")
                break
        
        if not memory_file:
            print("ERROR: memory_learning.py not found!")
            return False
        
        # Copy to both locations
        if memory_file != active_dir / "memory_learning.py":
            shutil.copy2(memory_file, active_dir / "memory_learning.py")
            print(f"Copied to: {active_dir / 'memory_learning.py'}")
            
        if memory_file != plugins_dir / "memory_learning.py":
            shutil.copy2(memory_file, plugins_dir / "memory_learning.py")
            print(f"Copied to: {plugins_dir / 'memory_learning.py'}")
        
        # Manually register the memory_learning module
        try:
            # Load module code
            with open(active_dir / "memory_learning.py", "r", encoding="utf-8", errors="replace") as f:
                memory_learning_code = f.read()
            
            # Create a module
            memory_module = type('memory_learning', (), {})
            exec(memory_learning_code, memory_module.__dict__)
            
            # Register in sys.modules
            sys.modules['plugins.memory_learning'] = memory_module
            sys.modules['plugins.active.memory_learning'] = memory_module
            print("Successfully registered memory_learning module")
        except Exception as e:
            print(f"Warning: Failed to create memory module: {e}")
        
        # Add scripts directory to path
        scripts_dir = current_dir / "scripts"
        sys.path.insert(0, str(scripts_dir))
        
        # Launch SassyQueenCore
        print("Launching SassyQueenCore...")
        try:
            spec = importlib.util.spec_from_file_location(
                "sassy_gui", 
                scripts_dir / "sassy_gui.py"
            )
            
            if not spec:
                print(f"Error: Could not find sassy_gui.py in {scripts_dir}")
                return False
                
            sassy_gui = importlib.util.module_from_spec(spec)
            sys.modules["sassy_gui"] = sassy_gui
            spec.loader.exec_module(sassy_gui)
            
            print("Starting GUI...")
            sassy_gui.main()
            return True
            
        except Exception as e:
            print(f"Error launching SassyQueenCore: {e}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"Setup error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        input("Press Enter to exit...")
"@

# Save Python script
$pythonScript | Out-File -FilePath "ps_fix_and_run.py" -Encoding utf8

# Check Python installation
try {
    $pythonVersion = python --version
    Write-Host "Using $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found in PATH." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Set Python UTF-8 mode
$env:PYTHONUTF8 = 1
$env:PYTHONIOENCODING = "utf-8"

# Run the fix and launch script
Write-Host "Running fix and launch script..." -ForegroundColor Yellow
python -X utf8 ps_fix_and_run.py

# Clean up
if (Test-Path ps_fix_and_run.py) {
    Remove-Item ps_fix_and_run.py
}

Write-Host "SassyQueenCore session ended." -ForegroundColor Cyan 