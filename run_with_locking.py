import sys 
import os 
from pathlib import Path 
 
# Load the database locking handler first 
try: 
    print("Applying database locking handler...") 
    import db_locking_handler 
    print("Database locking handler applied") 
except ImportError: 
    print("Database locking handler not found, continuing without it") 
 
# Now import and run the direct_run module 
try: 
    print("Starting SassyQueenCore...") 
    # Try different possible locations 
    try: 
        import direct_run 
        direct_run.main() 
    except ImportError: 
        # Look in parent directories 
        base_dir = Path(__file__).resolve().parent 
        parent_dir = base_dir.parent / "SassyQueenCore" 
        if (parent_dir / "direct_run.py").exists(): 
            sys.path.append(str(parent_dir)) 
            import direct_run 
            direct_run.main() 
        else: 
            print("ERROR: Could not find direct_run.py") 
except Exception as e: 
    print(f"Error running SassyQueenCore: {e}") 
