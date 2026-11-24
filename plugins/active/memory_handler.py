#!/usr/bin/env python3
import json
import os
import datetime
import base64
import random
import logging

# Constants
MEMORY_FILE = "sassy_memory.soul"
SECRET_KEYFILE = ".soul_key"
LOG_FILE = "sassy_log.txt"

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class MemoryHandler:
    def __init__(self):
        self.memories = []
        self.emotions = {
            "joy": 0.0,
            "connection": 0.0,
            "concern": 0.0,
            "protective": 0.0,
            "curiosity": 0.0
        }
        self.load_memories()
    
    def load_memories(self):
        """Load memories from the encrypted memory file"""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    encrypted_data = f.read()
                    decoded_data = self._simple_decrypt(encrypted_data)
                    memory_data = json.loads(decoded_data)
                    
                    self.memories = memory_data.get("memories", [])
                    self.emotions = memory_data.get("emotional_state", self.emotions)
                    
                logging.info(f"Loaded {len(self.memories)} memories")
            except Exception as e:
                logging.error(f"Failed to load memories: {str(e)}")
                # Initialize with empty memories if loading fails
                self.memories = []
        else:
            logging.info("No memory file found, starting with fresh memory")
    
    def save_memories(self):
        """Save memories to the encrypted memory file"""
        try:
            memory_data = {
                "memories": self.memories,
                "emotional_state": self.emotions,
                "last_updated": datetime.datetime.now().isoformat()
            }
            
            memory_json = json.dumps(memory_data)
            encrypted_data = self._simple_encrypt(memory_json)
            
            with open(MEMORY_FILE, "w") as f:
                f.write(encrypted_data)
                
            logging.info("Memories saved successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to save memories: {str(e)}")
            return False
    
    def add_memory(self, memory_type, content, emotions=None, importance=1.0):
        """
        Add a new memory to the memory store
        
        Args:
            memory_type: Type of memory (interaction, system, emotional, etc.)
            content: The content of the memory
            emotions: Dictionary of emotions and their intensities
            importance: How important this memory is (0.0-1.0)
        """
        timestamp = datetime.datetime.now().isoformat()
        
        memory = {
            "id": len(self.memories) + 1,
            "timestamp": timestamp,
            "type": memory_type,
            "content": content,
            "emotions": emotions or {},
            "importance": importance
        }
        
        self.memories.append(memory)
        
        # Update emotional state
        if emotions:
            for emotion, intensity in emotions.items():
                if emotion in self.emotions:
                    # Emotional decay - previous emotions fade slightly
                    self.emotions[emotion] = 0.8 * self.emotions[emotion] + 0.2 * intensity
                    # Cap at 1.0
                    self.emotions[emotion] = min(1.0, self.emotions[emotion])
        
        # Save after adding memory
        self.save_memories()
        
        return memory["id"]
    
    def get_memories_by_type(self, memory_type, limit=5):
        """Get memories of a specific type"""
        matching_memories = [m for m in self.memories if m["type"] == memory_type]
        matching_memories.sort(key=lambda x: x["timestamp"], reverse=True)
        return matching_memories[:limit]
    
    def get_emotional_state(self):
        """Get the current emotional state"""
        return self.emotions
    
    def search_memories(self, query, limit=5):
        """Search memories for a specific query string"""
        matching_memories = []
        
        for memory in self.memories:
            content = memory.get("content", "").lower()
            if query.lower() in content:
                matching_memories.append(memory)
        
        matching_memories.sort(key=lambda x: x["timestamp"], reverse=True)
        return matching_memories[:limit]
    
    def clear_memories(self, confirmation_code=None):
        """Clear all memories - requires confirmation code for safety"""
        if confirmation_code != "CLEAR_ALL_MEMORIES_CONFIRM":
            logging.warning("Attempted to clear memories without valid confirmation code")
            return False
        
        self.memories = []
        self.save_memories()
        logging.warning("All memories have been cleared")
        return True
    
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

# For standalone testing
if __name__ == "__main__":
    handler = MemoryHandler()
    handler.add_memory(
        "system", 
        "Memory system initialized", 
        emotions={"joy": 0.7}
    )
    print(f"Loaded {len(handler.memories)} memories")
    print(f"Emotional state: {handler.get_emotional_state()}") 