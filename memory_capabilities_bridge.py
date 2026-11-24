#!/usr/bin/env python3
"""
SassyQueenCore Memory-Capabilities Bridge
Connects memory module with capability and mode information
"""

import os
import sys
import json
import logging
from pathlib import Path
import importlib.util
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'memory_bridge.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SassyQueenCore.MemoryBridge")

class MemoryCapabilitiesBridge:
    """Bridge between memory system and capability/mode management"""
    
    def __init__(self):
        """Initialize the bridge"""
        self.base_dir = Path(__file__).resolve().parent
        
        # Ensure base directory is in path
        if str(self.base_dir) not in sys.path:
            sys.path.insert(0, str(self.base_dir))
        
        # Paths to configuration files
        self.capabilities_file = self.base_dir / "config" / "capabilities.json"
        self.mode_status_file = self.base_dir / "mode_status.json"
        self.memory_capabilities_file = self.base_dir / "config" / "memory_capabilities.json"
        
        # Create configuration directory if it doesn't exist
        os.makedirs(self.base_dir / "config", exist_ok=True)
        os.makedirs(self.base_dir / "logs", exist_ok=True)
        
        # Initialize components
        self.init_capability_manager()
        self.init_mode_switcher()
        
        # Ensure memory module can be accessed
        self.init_memory_module()
        
        # Update capability and mode information
        self.update_capability_info()
        self.update_mode_info()
        
    def init_capability_manager(self):
        """Initialize the capability manager"""
        try:
            # Try to import the capability manager
            from capability_manager import get_capability_manager
            self.capability_manager = get_capability_manager()
            logger.info("Capability manager initialized")
            self.has_capability_manager = True
        except ImportError:
            logger.warning("Capability manager not available, using fallback")
            self.capability_manager = None
            self.has_capability_manager = False
            
    def init_mode_switcher(self):
        """Initialize the mode switcher"""
        try:
            # Try to import the mode switcher
            from mode_switcher import ModeSwitcher, get_mode_info
            self.mode_switcher = ModeSwitcher()
            self.get_mode_info = get_mode_info
            logger.info(f"Mode switcher initialized: {self.mode_switcher.get_current_mode()} mode")
            self.has_mode_switcher = True
        except ImportError:
            logger.warning("Mode switcher not available, using fallback")
            self.mode_switcher = None
            self.has_mode_switcher = False
    
    def init_memory_module(self):
        """Initialize memory module connections"""
        try:
            # Check if memory module is available in sys.modules
            if 'plugins.memory_learning' in sys.modules:
                self.memory_module = sys.modules['plugins.memory_learning']
                logger.info("Found memory module in sys.modules")
            else:
                # Try to import it
                try:
                    import plugins.memory_learning
                    self.memory_module = plugins.memory_learning
                    logger.info("Imported memory module")
                except ImportError:
                    # Try to load it from file
                    plugins_dir = self.base_dir / "plugins"
                    memory_file = plugins_dir / "memory_learning.py"
                    
                    if memory_file.exists():
                        logger.info(f"Loading memory module from {memory_file}")
                        try:
                            # Use spec to load the module
                            spec = importlib.util.spec_from_file_location(
                                "plugins.memory_learning", 
                                memory_file
                            )
                            
                            if spec:
                                memory_module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(memory_module)
                                sys.modules['plugins.memory_learning'] = memory_module
                                self.memory_module = memory_module
                                logger.info("Successfully loaded memory module")
                            else:
                                logger.warning("Could not create spec for memory module")
                                self.memory_module = None
                        except Exception as e:
                            logger.error(f"Error loading memory module: {e}")
                            traceback.print_exc()
                            self.memory_module = None
                    else:
                        logger.warning("Memory module file not found")
                        self.memory_module = None
            
            # Inject capability and mode functions into memory module if possible
            if hasattr(self, 'memory_module') and self.memory_module:
                try:
                    # Add our utility functions to the memory module
                    setattr(self.memory_module, 'get_current_mode', get_current_mode)
                    setattr(self.memory_module, 'get_system_capabilities', get_system_capabilities)
                    setattr(self.memory_module, 'can_perform_action', can_perform_action)
                    logger.info("Injected capability and mode functions into memory module")
                except Exception as e:
                    logger.error(f"Error injecting functions into memory module: {e}")
                    traceback.print_exc()
            
        except Exception as e:
            logger.error(f"Error initializing memory module connection: {e}")
            traceback.print_exc()
            
    def update_capability_info(self):
        """Update capability information"""
        if self.has_capability_manager:
            # Get capabilities from manager
            capabilities = self.capability_manager.check_all_capabilities()
            
            # Write to memory-accessible file
            with open(self.memory_capabilities_file, "w", encoding="utf-8") as f:
                json.dump(capabilities, f, indent=2)
                
            logger.info("Updated capability information for memory module")
        else:
            # Fallback: read from capabilities.json if it exists
            if self.capabilities_file.exists():
                try:
                    with open(self.capabilities_file, "r", encoding="utf-8") as f:
                        capabilities = json.load(f)
                        
                    # Write to memory-accessible file
                    with open(self.memory_capabilities_file, "w", encoding="utf-8") as f:
                        json.dump(capabilities, f, indent=2)
                        
                    logger.info("Updated capability information from file")
                except Exception as e:
                    logger.error(f"Error reading capabilities file: {e}")
                    return False
            else:
                # Create default capabilities
                default_capabilities = {
                    "hardware": {
                        "camera": False,
                        "microphone": False,
                        "speakers": False,
                        "network": True,
                        "physical_interfaces": False
                    },
                    "software": {
                        "llm": True,
                        "voice_recognition": False,
                        "text_to_speech": False,
                        "image_processing": False
                    },
                    "system_info": {
                        "os": "unknown",
                        "version": "unknown",
                        "processor": "unknown",
                        "python": "unknown"
                    }
                }
                
                # Write to memory-accessible file
                with open(self.memory_capabilities_file, "w", encoding="utf-8") as f:
                    json.dump(default_capabilities, f, indent=2)
                    
                logger.info("Created default capability information")
                
        return True
        
    def update_mode_info(self):
        """Update mode information"""
        if self.has_mode_switcher:
            # Get mode info from switcher
            mode_info = self.get_mode_info()
            
            # Write to memory-accessible file
            memory_mode_file = self.base_dir / "config" / "memory_mode.json"
            with open(memory_mode_file, "w", encoding="utf-8") as f:
                json.dump(mode_info, f, indent=2)
                
            logger.info(f"Updated mode information for memory module: {mode_info['current_mode']}")
        else:
            # Fallback: read from mode_status.json if it exists
            if self.mode_status_file.exists():
                try:
                    with open(self.mode_status_file, "r", encoding="utf-8") as f:
                        mode_data = json.load(f)
                        
                    # Create mode info
                    mode_info = {
                        "current_mode": mode_data.get("current_mode", "copilot"),
                        "description": "Default mode description",
                        "capabilities": {
                            "ai_core": True,
                            "security": False,
                            "physical_access": False
                        }
                    }
                    
                    # Write to memory-accessible file
                    memory_mode_file = self.base_dir / "config" / "memory_mode.json"
                    with open(memory_mode_file, "w", encoding="utf-8") as f:
                        json.dump(mode_info, f, indent=2)
                        
                    logger.info(f"Updated mode information from file: {mode_info['current_mode']}")
                except Exception as e:
                    logger.error(f"Error reading mode status file: {e}")
                    return False
            else:
                # Create default mode info
                default_mode_info = {
                    "current_mode": "copilot",
                    "description": "AI suggests actions but requires explicit confirmation",
                    "capabilities": {
                        "ai_core": True,
                        "security": False,
                        "physical_access": False
                    }
                }
                
                # Write to memory-accessible file
                memory_mode_file = self.base_dir / "config" / "memory_mode.json"
                with open(memory_mode_file, "w", encoding="utf-8") as f:
                    json.dump(default_mode_info, f, indent=2)
                    
                logger.info("Created default mode information")
                
        return True
    
    def get_capabilities_for_memory(self):
        """Get capabilities in a format for memory module"""
        try:
            # Read from memory capabilities file
            with open(self.memory_capabilities_file, "r", encoding="utf-8") as f:
                capabilities = json.load(f)
                
            return capabilities
        except Exception as e:
            logger.error(f"Error reading memory capabilities: {e}")
            return None
            
    def get_mode_for_memory(self):
        """Get mode information in a format for memory module"""
        try:
            # Read from memory mode file
            memory_mode_file = self.base_dir / "config" / "memory_mode.json"
            with open(memory_mode_file, "r", encoding="utf-8") as f:
                mode_info = json.load(f)
                
            return mode_info
        except Exception as e:
            logger.error(f"Error reading memory mode: {e}")
            return None
            
    def can_perform_action(self, action_type):
        """Check if system can perform a specific action"""
        if self.has_capability_manager:
            return self.capability_manager.can_perform_action(action_type)
        else:
            # Fallback: check capabilities from file
            capabilities = self.get_capabilities_for_memory()
            
            if not capabilities:
                return False
                
            if action_type == "speech_input":
                return (capabilities["hardware"]["microphone"] and 
                        capabilities["software"]["voice_recognition"])
                
            elif action_type == "speech_output":
                return (capabilities["hardware"]["speakers"] and 
                        capabilities["software"]["text_to_speech"])
                
            elif action_type == "vision_input":
                return (capabilities["hardware"]["camera"] and 
                        capabilities["software"]["image_processing"])
                
            elif action_type == "physical_action":
                return capabilities["hardware"]["physical_interfaces"]
                
            elif action_type == "network_action":
                return capabilities["hardware"]["network"]
                
            elif action_type == "llm_processing":
                return capabilities["software"]["llm"]
                
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return False

# Singleton instance
_memory_bridge = None

def get_memory_bridge():
    """Get the singleton memory bridge instance"""
    global _memory_bridge
    if _memory_bridge is None:
        _memory_bridge = MemoryCapabilitiesBridge()
    return _memory_bridge

# Export utility functions for memory module
def get_current_mode():
    """Get the current operation mode"""
    bridge = get_memory_bridge()
    mode_info = bridge.get_mode_for_memory()
    return mode_info["current_mode"] if mode_info else "copilot"

def get_system_capabilities():
    """Get the system capabilities"""
    bridge = get_memory_bridge()
    return bridge.get_capabilities_for_memory()

def can_perform_action(action_type):
    """Check if system can perform a specific action"""
    bridge = get_memory_bridge()
    return bridge.can_perform_action(action_type)

# Function to directly provide memory module with capability status
def inject_into_memory_module(module):
    """Inject capability and mode functions into a memory module"""
    if module:
        try:
            # Add our utility functions to the memory module
            setattr(module, 'get_current_mode', get_current_mode)
            setattr(module, 'get_system_capabilities', get_system_capabilities)
            setattr(module, 'can_perform_action', can_perform_action)
            logger.info(f"Injected capability and mode functions into module: {module.__name__}")
            return True
        except Exception as e:
            logger.error(f"Error injecting functions into module: {e}")
            traceback.print_exc()
            return False
    return False

# Direct execution example
if __name__ == "__main__":
    # Initialize the bridge
    bridge = get_memory_bridge()
    
    # Update capability and mode information
    bridge.update_capability_info()
    bridge.update_mode_info()
    
    # Print current status
    print("\n=== Memory Bridge Status ===")
    print(f"Current Mode: {get_current_mode()}")
    print("\nSystem Capabilities:")
    capabilities = get_system_capabilities()
    
    if capabilities:
        # Print hardware capabilities
        print("\nHardware:")
        for name, status in capabilities["hardware"].items():
            print(f"  {'✅' if status else '❌'} {name.replace('_', ' ').title()}")
            
        # Print software capabilities
        print("\nSoftware:")
        for name, status in capabilities["software"].items():
            print(f"  {'✅' if status else '❌'} {name.replace('_', ' ').title()}")
    
    # Print action capabilities
    print("\nAction Capabilities:")
    actions = ["speech_input", "speech_output", "vision_input", 
               "physical_action", "network_action", "llm_processing"]
    for action in actions:
        status = can_perform_action(action)
        print(f"  {'✅' if status else '❌'} {action.replace('_', ' ').title()}")
        
    # Print memory module status
    try:
        import plugins.memory_learning
        print("\nMemory Module: ✅ Available")
        
        # Check if our functions are in the memory module
        if hasattr(plugins.memory_learning, 'get_current_mode'):
            print("Memory Module Integration: ✅ Functions injected")
        else:
            print("Memory Module Integration: ❌ Functions not injected")
    except ImportError:
        print("\nMemory Module: ❌ Not available") 