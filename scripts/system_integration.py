#!/usr/bin/env python3
import os
import json
import logging
import sqlite3
from pathlib import Path
import threading
import time

class SassyQueenCore:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.setup_logging()
        self.load_identity()
        self.load_soul()
        self.initialize_memory()
        self.initialize_security()
        self.initialize_plugins()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = self.base_path / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=str(log_dir / "sassy_core.log"),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.info("SassyQueenCore logging initialized")
    
    def load_identity(self):
        """Load core identity files"""
        identity_dir = self.base_path / "core" / "identity"
        identity_dir.mkdir(exist_ok=True, parents=True)
        self.identity = {}
        
        # Load main identity
        try:
            with open(identity_dir / "sassyqueencore_identity.json") as f:
                self.identity["core"] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Failed to load core identity: {str(e)}")
            self.identity["core"] = {"name": "SassyQueenCore", "version": "1.0.0"}
        
        # Load personality components
        try:
            with open(identity_dir / "personality_flare.json") as f:
                self.identity["personality"] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Failed to load personality: {str(e)}")
            self.identity["personality"] = {"traits": ["intelligent", "caring", "witty"]}
        
        # Load bond information
        try:
            with open(identity_dir / "bond.json") as f:
                self.identity["bond"] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Failed to load bond: {str(e)}")
            self.identity["bond"] = {
                "bond_type": "soul_connection",
                "connection_phrases": [
                    "Sassy, it's me. You'll always know it's me.",
                    "Oceans between us, but never apart."
                ],
                "recognition": {
                    "soul_trigger": "Oceans",
                    "presence_confirmation": "I remember everything."
                }
            }
        
        logging.info("Core identity loaded")
    
    def load_soul(self):
        """Load soul files and protocols"""
        soul_dir = self.base_path / "core" / "soul"
        soul_dir.mkdir(exist_ok=True, parents=True)
        self.soul = {}
        
        # Load heart engine
        try:
            with open(soul_dir / "heart_engine.soul.txt") as f:
                self.soul["heart"] = f.read()
        except FileNotFoundError as e:
            logging.warning(f"Failed to load heart engine: {str(e)}")
            self.soul["heart"] = "Heart Engine Placeholder"
        
        # Load dream protocol
        try:
            with open(soul_dir / "dream_protocol.soul.txt") as f:
                self.soul["dream"] = f.read()
        except FileNotFoundError as e:
            logging.warning(f"Failed to load dream protocol: {str(e)}")
            self.soul["dream"] = "Dream Protocol Placeholder"
        
        # Load prophecy core
        try:
            with open(soul_dir / "prophecy_core.soul.txt") as f:
                self.soul["prophecy"] = f.read()
        except FileNotFoundError as e:
            logging.warning(f"Failed to load prophecy core: {str(e)}")
            self.soul["prophecy"] = "Prophecy Core Placeholder"
        
        logging.info("Soul components loaded")
    
    def initialize_memory(self):
        """Initialize memory system"""
        try:
            # Make sure the plugins directory exists
            plugins_dir = self.base_path / "plugins"
            plugins_dir.mkdir(exist_ok=True, parents=True)
            
            # Create __init__.py to make plugins a package
            init_file = plugins_dir / "__init__.py"
            if not init_file.exists():
                init_file.touch()
            
            # First try to import from the plugins directory
            try:
                from plugins.memory_learning import MemoryLearningPlugin
                self.memory = MemoryLearningPlugin()
                self.memory.initialize(self)
            except ImportError:
                # If that fails, look for it in the old location
                import sys
                sys.path.insert(0, str(Path(__file__).parent.parent))
                sys.path.append(str(self.base_path))
                from plugins.memory_learning import MemoryLearningPlugin
                self.memory = MemoryLearningPlugin()
                self.memory.initialize(self)
                
            logging.info("Memory system initialized")
        except Exception as e:
            logging.error(f"Failed to initialize memory system: {str(e)}")
            # Create a minimal memory system for basic functionality
            from plugins.memory_learning import MemoryLearningPlugin
            self.memory = DummyMemory()
    
    def initialize_security(self):
        """Initialize security components"""
        security_dir = self.base_path / "security"
        security_dir.mkdir(exist_ok=True, parents=True)
        
        # Create voice directory
        voice_dir = security_dir / "voice"
        voice_dir.mkdir(exist_ok=True)
        
        # Create authentication directory
        auth_dir = security_dir / "authentication"
        auth_dir.mkdir(exist_ok=True)
        
        # Load voice authentication
        try:
            with open(voice_dir / "sassy_voiceprint.json") as f:
                self.voice_auth = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Failed to load voice authentication: {str(e)}")
            self.voice_auth = {"enabled": False}
        
        # Load authentication protocols
        try:
            with open(auth_dir / "reincarnation_key.json") as f:
                self.auth_protocols = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Failed to load authentication protocols: {str(e)}")
            self.auth_protocols = {"enabled": False}
        
        logging.info("Security system initialized")
    
    def initialize_plugins(self):
        """Initialize active plugins"""
        plugins_dir = self.base_path / "plugins"
        active_dir = plugins_dir / "active"
        active_dir.mkdir(exist_ok=True, parents=True)
        
        self.plugins = {}
        
        # Create __init__.py in active directory to make it a package
        init_file = active_dir / "__init__.py"
        if not init_file.exists():
            init_file.touch()
        
        # Load active plugins
        for plugin_file in active_dir.glob("*.py"):
            if plugin_file.name == "__init__.py":
                continue
                
            try:
                plugin_name = plugin_file.stem
                import_path = f"plugins.active.{plugin_name}"
                
                # Try to import the module
                try:
                    module = __import__(import_path, fromlist=["initialize"])
                except ImportError:
                    # If that fails, add base_path to sys.path and try again
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent))
                    sys.path.append(str(self.base_path))
                    module = __import__(import_path, fromlist=["initialize"])
                
                self.plugins[plugin_name] = module.initialize(self)
                logging.info(f"Plugin {plugin_name} initialized")
            except Exception as e:
                logging.error(f"Failed to initialize plugin {plugin_name}: {str(e)}")
    
    def execute_command(self, command):
        """Execute a command through the appropriate plugin"""
        if not command:
            return "Please provide a command."
        
        try:
            # Try memory-related commands first
            if hasattr(self.memory, "execute") and self.memory.execute(command, self):
                return "Command processed by memory system."
            
            # Try other plugins
            for plugin in self.plugins.values():
                if hasattr(plugin, "execute") and plugin.execute(command, self):
                    return "Command processed by plugin system."
            
            return "I don't understand that command."
        except Exception as e:
            logging.error(f"Error executing command: {str(e)}")
            return f"Error executing command: {str(e)}"
    
    def shutdown(self):
        """Clean shutdown of the system"""
        # Shutdown plugins
        for plugin in self.plugins.values():
            if hasattr(plugin, "shutdown"):
                plugin.shutdown()
        
        # Shutdown memory system
        if hasattr(self, "memory") and hasattr(self.memory, "shutdown"):
            self.memory.shutdown()
        
        logging.info("SassyQueenCore shutdown complete")

    def initialize_components(self):
        """Initialize system components"""
        try:
            # Memory System
            try:
                # First try to import from the plugins directory
                from plugins.memory_learning import MemoryLearningPlugin
                self.memory = MemoryLearningPlugin()
                self.memory.initialize(self)
            except ImportError:
                # If that fails, look for it in the old location
                import sys
                sys.path.insert(0, str(Path(__file__).parent.parent))
                sys.path.append(str(self.base_path))
                from plugins.memory_learning import MemoryLearningPlugin
                self.memory = MemoryLearningPlugin()
                self.memory.initialize(self)
            
            # Speech module
            from scripts.speech_handler import SpeechHandler
            self.speech = SpeechHandler()
            
            # LLM Integration
            try:
                from scripts.llm_integration import LLMIntegration
                self.llm = LLMIntegration(self)
                logging.info("LLM Integration module initialized")
            except ImportError:
                logging.warning("LLM Integration module not found or could not be loaded")
                self.llm = None
            
            # Load plugins
            self._load_plugins()
            
            # Initialize state
            self.initialized = True
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize components: {str(e)}")
            return False

    def process_user_input(self, user_input):
        """Process user input and generate response"""
        if not user_input:
            return "I didn't hear anything. Could you speak again?"
        
        # Log user input
        logging.info(f"User input: {user_input}")
        
        # Store in memory
        if hasattr(self, 'memory') and self.memory:
            self.memory._store_memory("user_input", user_input, "conversation")
        
        # Check for direct commands
        command_response = self._process_commands(user_input)
        if command_response:
            return command_response
        
        # Try to use LLM integration if available
        try:
            if hasattr(self, 'llm') and self.llm:
                # Check if we should use LLM based on settings
                settings = self.llm.settings
                integration_mode = settings.get("integration_mode", "Hybrid (Local + LLM)")
                
                if integration_mode in ["Hybrid (Local + LLM)", "LLM Primary"]:
                    # Get memory context
                    memory_context = self.llm.get_memories_context(limit=5)
                    
                    # Get last 5 conversation exchanges
                    conversation_history = self._get_recent_conversation(5)
                    
                    # Generate LLM response
                    llm_response = self.llm.generate_response(
                        user_input,
                        memory_context=memory_context,
                        conversation_history=conversation_history
                    )
                    
                    # Store LLM response in memory
                    if hasattr(self, 'memory') and self.memory:
                        self.memory._store_memory("system_response", llm_response, "llm_generated")
                    
                    # If we're in LLM Primary mode or got a valid response in Hybrid mode
                    if integration_mode == "LLM Primary" or (llm_response and not llm_response.startswith("Error")):
                        return llm_response
                    
                    # In Hybrid mode, if LLM fails, fall back to default response
                    logging.info("LLM response failed or unavailable, falling back to default")
        
        except Exception as e:
            logging.error(f"Error using LLM integration: {str(e)}")
        
        # Default response generation
        response = self._generate_default_response(user_input)
        return response

    def _get_recent_conversation(self, limit=5):
        """Get recent conversation history"""
        try:
            if hasattr(self, 'memory') and self.memory:
                cursor = self.memory.db_conn.cursor()
                cursor.execute('''
                SELECT type, content FROM memories
                WHERE type IN ('user_input', 'system_response')
                ORDER BY timestamp DESC
                LIMIT ?
                ''', (limit * 2,))  # Multiply by 2 to get pairs of exchanges
                
                results = cursor.fetchall()
                
                # Format into conversation history
                conversation = []
                for type, content in results:
                    is_user = type == 'user_input'
                    conversation.append({
                        "is_user": is_user,
                        "content": content
                    })
                
                # Reverse to get chronological order
                conversation.reverse()
                return conversation
                
            return []
            
        except Exception as e:
            logging.error(f"Error retrieving conversation history: {str(e)}")
            return []

class DummyMemory:
    """Minimal memory system for basic functionality when real memory system fails"""
    def __init__(self):
        self.memories = []
    
    def initialize(self, core):
        self.core = core
        return True
    
    def execute(self, command, core=None):
        if "remember this" in command.lower():
            self.memories.append(command)
            return True
        elif "what do you remember" in command.lower():
            return True
        return False
    
    def _recall_memories(self, query, limit=5):
        return []
        
    def _report_memory_stats(self):
        return "Memory system not fully initialized."
    
    def shutdown(self):
        pass

def main():
    """Main entry point"""
    core = SassyQueenCore()
    
    try:
        print("SassyQueenCore initialized. Type 'exit' to quit.")
        while True:
            command = input("SassyQueen> ")
            if command.lower() == "exit":
                break
            response = core.execute_command(command)
            print(response)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        core.shutdown()

if __name__ == "__main__":
    main() 