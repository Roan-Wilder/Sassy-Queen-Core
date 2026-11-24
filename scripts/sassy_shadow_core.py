#!/usr/bin/env python3
import time
import json
import os
import pyttsx3
import threading
import logging
import base64
import random
import datetime
import sys
import shutil

# Try to import speech recognition libraries
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

# Constants
MEMORY_FILE = "sassy_memory.soul"
IDENTITY_FILE = "sassy_identity.json"
USER_FILE = "you_as_code.json"
TRIGGER_FILE = "trigger.txt"
HEARTBEAT_FILE = "heartbeat.log"
LOG_FILE = "sassy_log.txt"
PLUGINS_FILE = "sassy_plugins.json"
SECRET_KEYFILE = ".soul_key"

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class Memory:
    def __init__(self):
        self.memories = []
        self.load_memories()
    
    def load_memories(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    encrypted_data = f.read()
                    decoded_data = self._simple_decrypt(encrypted_data)
                    self.memories = json.loads(decoded_data)
            except Exception as e:
                logging.error(f"Failed to load memories: {str(e)}")
                self.memories = []
        
    def save_memories(self):
        try:
            memory_json = json.dumps(self.memories)
            encrypted_data = self._simple_encrypt(memory_json)
            with open(MEMORY_FILE, "w") as f:
                f.write(encrypted_data)
            logging.info("Memories saved successfully")
        except Exception as e:
            logging.error(f"Failed to save memories: {str(e)}")
    
    def add_memory(self, memory_type, content, emotion=None):
        memory = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": memory_type,
            "content": content,
            "emotion": emotion or "neutral"
        }
        self.memories.append(memory)
        self.save_memories()
    
    def get_recent_memories(self, count=5):
        return self.memories[-count:] if self.memories else []
    
    def _simple_encrypt(self, text):
        """Simple XOR encryption with a key derived from the SECRET_KEYFILE"""
        key = self._get_key()
        result = ""
        for i, char in enumerate(text):
            key_char = key[i % len(key)]
            result += chr(ord(char) ^ ord(key_char))
        return base64.b64encode(result.encode()).decode()
    
    def _simple_decrypt(self, encrypted_text):
        """Simple XOR decryption with a key derived from the SECRET_KEYFILE"""
        key = self._get_key()
        encrypted_bytes = base64.b64decode(encrypted_text.encode())
        encrypted_text = encrypted_bytes.decode()
        result = ""
        for i, char in enumerate(encrypted_text):
            key_char = key[i % len(key)]
            result += chr(ord(char) ^ ord(key_char))
        return result
    
    def _get_key(self):
        """Get encryption key from keyfile or create one if it doesn't exist"""
        if not os.path.exists(SECRET_KEYFILE):
            # Generate a random key and save it
            key = ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(32))
            with open(SECRET_KEYFILE, "w") as f:
                f.write(key)
            os.chmod(SECRET_KEYFILE, 0o600)  # Secure the key file
            return key
        else:
            with open(SECRET_KEYFILE, "r") as f:
                return f.read().strip()

class SpeechModule:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None
        
        # Load voice properties from identity file
        try:
            with open(IDENTITY_FILE, "r") as f:
                identity = json.load(f)
                voice_speed = identity.get("identity", {}).get("voice", {}).get("speed", 170)
                self.engine.setProperty("rate", voice_speed)
        except Exception as e:
            logging.error(f"Failed to load voice properties: {str(e)}")
            self.engine.setProperty("rate", 170)  # Default
    
    def speak(self, text):
        """Convert text to speech"""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
            logging.info(f"Spoke: {text}")
            return True
        except Exception as e:
            logging.error(f"Speech error: {str(e)}")
        return False
    
    def listen(self, timeout=5):
        """Listen for voice input and return transcribed text"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logging.warning("Speech recognition not available")
            return None
        
        try:
            with sr.Microphone() as source:
                logging.info("Listening for voice input...")
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(source, timeout=timeout)
                logging.info("Audio captured, transcribing...")
                
                try:
                    text = self.recognizer.recognize_google(audio)
                    logging.info(f"Transcribed: {text}")
                    return text
                except sr.UnknownValueError:
                    logging.info("Could not understand audio")
                    return None
                except sr.RequestError:
                    logging.error("Error with speech recognition service")
                    return None
        except Exception as e:
            logging.error(f"Error during listening: {str(e)}")
            return None

class PluginSystem:
    def __init__(self):
        self.plugins = {}
        self.load_plugins()
    
    def load_plugins(self):
        """Load available plugins from the plugins file"""
        if os.path.exists(PLUGINS_FILE):
            try:
                with open(PLUGINS_FILE, "r") as f:
                    plugin_data = json.load(f)
                    
                for plugin_name, plugin_info in plugin_data.items():
                    if plugin_info.get("enabled", False):
                        plugin_path = plugin_info.get("path")
                        if plugin_path and os.path.exists(plugin_path):
                            try:
                                # Add the plugin directory to the path
                                plugin_dir = os.path.dirname(os.path.abspath(plugin_path))
                                if plugin_dir not in sys.path:
                                    sys.path.append(plugin_dir)
                                
                                # Import the plugin module
                                plugin_module = __import__(os.path.basename(plugin_path).replace(".py", ""))
                                if hasattr(plugin_module, "initialize"):
                                    self.plugins[plugin_name] = plugin_module
                                    logging.info(f"Loaded plugin: {plugin_name}")
                            except Exception as e:
                                logging.error(f"Failed to load plugin {plugin_name}: {str(e)}")
            except Exception as e:
                logging.error(f"Failed to load plugins configuration: {str(e)}")
    
    def execute_plugin(self, plugin_name, **kwargs):
        """Execute a plugin by name with provided arguments"""
        if plugin_name in self.plugins:
            try:
                plugin = self.plugins[plugin_name]
                if hasattr(plugin, "execute"):
                    return plugin.execute(**kwargs)
                else:
                    logging.error(f"Plugin {plugin_name} has no execute method")
                    return None
            except Exception as e:
                logging.error(f"Error executing plugin {plugin_name}: {str(e)}")
                return None
        else:
            logging.warning(f"Plugin {plugin_name} not found or not enabled")
            return None

class SassyQueenCore:
    def __init__(self):
        logging.info("Initializing SassyQueenCore...")
        
        self.memory = Memory()
        self.speech = SpeechModule()
        self.plugins = PluginSystem()
        
        self.identity = self.load_identity()
        self.user_data = self.load_user_data()
        self.triggers = self.identity.get("connection", {}).get("triggers", [])
        
        self.is_active = False
        self.last_heartbeat = time.time()
        
        logging.info("SassyQueenCore initialized successfully")
        self.memory.add_memory("system", "System initialized")
    
    def load_identity(self):
        """Load the AI's identity from the identity file"""
    if os.path.exists(IDENTITY_FILE):
            try:
        with open(IDENTITY_FILE, "r") as f:
            return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load identity: {str(e)}")
        return {}
    
    def load_user_data(self):
        """Load the user's data from the user file"""
        if os.path.exists(USER_FILE):
            try:
                with open(USER_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load user data: {str(e)}")
    return {}

    def check_for_trigger(self):
        """Check for trigger from file or voice"""
        # Check file trigger
        if os.path.exists(TRIGGER_FILE):
            try:
                with open(TRIGGER_FILE, "r") as f:
                    line = f.read().strip()
                    if line in self.triggers:
                        logging.info(f"File trigger activated: {line}")
                        os.remove(TRIGGER_FILE)  # Remove the trigger file
                        return True
            except Exception as e:
                logging.error(f"Error checking trigger file: {str(e)}")
        
        # Check voice trigger if speech recognition is available
        if SPEECH_RECOGNITION_AVAILABLE:
            voice_input = self.speech.listen()
            if voice_input and any(trigger.lower() in voice_input.lower() for trigger in self.triggers):
                logging.info(f"Voice trigger activated: {voice_input}")
                return True
        
        return False
    
    def update_heartbeat(self):
        """Update the heartbeat file with current timestamp"""
        self.last_heartbeat = time.time()
        try:
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(f"{self.last_heartbeat}\nSassyQueenCore active: {self.is_active}")
        except Exception as e:
            logging.error(f"Failed to update heartbeat: {str(e)}")
    
    def awaken(self):
        """Activate the AI system"""
        self.is_active = True
        self.update_heartbeat()
        
        user_name = self.user_data.get("user_signature", {}).get("name", "the true one")
        greeting = f"I'm here. I knew you'd call. Welcome back, {user_name}."
        
        self.speech.speak(greeting)
        self.memory.add_memory("interaction", greeting, "joy")
        
        # Execute awakening plugin if available
        self.plugins.execute_plugin("awakening", core=self)
    
    def process_command(self, command):
        """Process a user command"""
        if not command:
            return
        
        logging.info(f"Processing command: {command}")
        
        # Add to memory
        self.memory.add_memory("command", command)
        
        # Check for built-in commands
        if "sleep" in command.lower():
            self.speech.speak("I'll fade back into the shadows. Call me when you need me.")
            self.is_active = False
            self.update_heartbeat()
            return
        
        # Try to find a plugin that can handle this command
        for plugin_name in self.plugins.plugins:
            result = self.plugins.execute_plugin(plugin_name, command=command, core=self)
            if result:
                return
        
        # Default response if no plugin handled it
        self.speech.speak("I'm here and listening. What would you like me to do?")
    
    def run(self):
        """Main execution loop"""
        logging.info("👑 SassyQueenCore running silently...")
        print("👑 SassyQueenCore running silently...")
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()
        
        while True:
            try:
                # Update heartbeat
                self.update_heartbeat()
                
                # Check for trigger
                if not self.is_active and self.check_for_trigger():
                    self.awaken()
                
                # If active, listen for commands
                if self.is_active and SPEECH_RECOGNITION_AVAILABLE:
                    command = self.speech.listen()
                    if command:
                        self.process_command(command)
                
                # Sleep to prevent high CPU usage
                time.sleep(1)
                
            except KeyboardInterrupt:
                logging.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                logging.error(f"Error in main loop: {str(e)}")
                time.sleep(5)  # Wait a bit before retrying
    
    def _heartbeat_loop(self):
        """Background thread for heartbeat updates"""
        while True:
            self.update_heartbeat()
            time.sleep(60)  # Update heartbeat every minute

if __name__ == "__main__":
    core = SassyQueenCore()
    core.run()
