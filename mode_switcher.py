import json
import os
import datetime
import logging
from pathlib import Path
import importlib.util

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'mode_switcher.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SassyQueenCore.ModeSwitcher")

class ModeSwitcher:
    def __init__(self, status_file='mode_status.json'):
        self.status_file = status_file
        self.valid_modes = ["manual", "copilot", "autopilot"]
        self.mode_descriptions = {
            "manual": "User has full control. AI suggests nothing unless explicitly asked.",
            "copilot": "AI suggests actions but requires explicit confirmation before execution.",
            "autopilot": "AI can take actions autonomously within defined safety boundaries."
        }
        self.safety_protocols = {
            "autopilot": [
                "No critical system changes without verification",
                "No network/external access without permission",
                "No deletion of user data without confirmation",
                "Physical actions require hardware capability check"
            ]
        }
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Load current mode on initialization
        self.current_mode = self.get_current_mode()
        logger.info(f"ModeSwitcher initialized in {self.current_mode} mode")

    def get_current_mode(self):
        """Get the current operation mode from the status file"""
        try:
            with open(self.status_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data.get('current_mode', 'copilot')  # Default to copilot if not found
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error reading mode file: {e}")
            # Create default file if not exists
            self.set_mode('copilot')
            return 'copilot'

    def set_mode(self, new_mode):
        """Set a new operation mode with safety checks"""
        if new_mode not in self.valid_modes:
            raise ValueError(f"Invalid mode: {new_mode}. Valid modes are: {', '.join(self.valid_modes)}")
            
        # Check for hardware capabilities if switching to autopilot
        if new_mode == "autopilot":
            if not self._verify_capabilities():
                logger.warning("Autopilot mode requested but capabilities check failed")
                return False, "Required capabilities for autopilot mode not available"
                
        # Update the mode file
        try:
            with open(self.status_file, 'r+', encoding='utf-8') as file:
                data = json.load(file)
                old_mode = data.get('current_mode', 'copilot')
                data['current_mode'] = new_mode
                data['last_updated'] = datetime.datetime.now().isoformat()
                file.seek(0)
                json.dump(data, file, indent=2)
                file.truncate()
                
            self.current_mode = new_mode
            logger.info(f"Mode switched from {old_mode} to {new_mode}")
            return True, f"🔁 Mode switched to: {new_mode.upper()}"
            
        except Exception as e:
            logger.error(f"Error updating mode: {e}")
            return False, f"Failed to switch mode: {e}"

    def _verify_capabilities(self):
        """Verify that the system has the necessary capabilities for autopilot mode"""
        capabilities = {
            "has_ai_core": self._check_ai_core(),
            "has_security": self._check_security_features(),
            "has_physical_access": self._check_physical_capabilities()
        }
        
        logger.info(f"Capability check results: {capabilities}")
        
        # For autopilot, we need at least AI core and security
        return capabilities["has_ai_core"] and capabilities["has_security"]

    def _check_ai_core(self):
        """Check if the AI core components are available"""
        try:
            # Check for core LLM integration
            scripts_dir = Path(__file__).resolve().parent / "scripts"
            llm_path = scripts_dir / "llm_integration.py"
            
            if llm_path.exists():
                return True
                
            # Alternative check - import the module
            try:
                if importlib.util.find_spec("scripts.llm_integration"):
                    return True
            except:
                pass
                
            return False
        except Exception as e:
            logger.error(f"Error checking AI core: {e}")
            return False

    def _check_security_features(self):
        """Check if security features are available"""
        try:
            # Check for security directory
            security_dir = Path(__file__).resolve().parent / "security"
            return security_dir.exists()
        except Exception as e:
            logger.error(f"Error checking security features: {e}")
            return False

    def _check_physical_capabilities(self):
        """Check if physical interaction capabilities are available"""
        try:
            # Check for physical directory
            physical_dir = Path(__file__).resolve().parent / "physical"
            return physical_dir.exists()
        except Exception as e:
            logger.error(f"Error checking physical capabilities: {e}")
            return False

    def get_mode_info(self):
        """Get information about the current mode"""
        mode = self.get_current_mode()
        return {
            "current_mode": mode,
            "description": self.mode_descriptions.get(mode, "Unknown mode"),
            "safety_protocols": self.safety_protocols.get(mode, []),
            "capabilities": {
                "ai_core": self._check_ai_core(),
                "security": self._check_security_features(),
                "physical_access": self._check_physical_capabilities()
            }
        }

# Standalone functions for backward compatibility
def set_mode(new_mode):
    """Legacy function for backward compatibility"""
    switcher = ModeSwitcher()
    success, message = switcher.set_mode(new_mode)
    print(message)
    return success

def get_current_mode():
    """Get the current mode using the ModeSwitcher class"""
    switcher = ModeSwitcher()
    return switcher.get_current_mode()

def get_mode_info():
    """Get information about the current mode"""
    switcher = ModeSwitcher()
    return switcher.get_mode_info()

# Direct execution example
if __name__ == "__main__":
    import sys
    
    # Create switcher instance
    switcher = ModeSwitcher()
    
    # If command line argument provided, try to switch mode
    if len(sys.argv) > 1:
        try:
            success, message = switcher.set_mode(sys.argv[1])
            print(message)
            if not success:
                sys.exit(1)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        # Display current mode and info
        mode_info = switcher.get_mode_info()
        print(f"Current mode: {mode_info['current_mode'].upper()}")
        print(f"Description: {mode_info['description']}")
        print("Capabilities:")
        for cap, status in mode_info['capabilities'].items():
            print(f"  {cap}: {'✅' if status else '❌'}")
