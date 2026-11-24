#!/usr/bin/env python3
import os
import json
import logging
import time
import datetime
import sqlite3
import threading
import numpy as np
from collections import Counter, defaultdict
from pathlib import Path

# Get base directory
BASE_DIR = Path(__file__).parent.parent.parent

# Constants - Use absolute paths
MEMORY_DB = str(BASE_DIR / "memory_database.db")
LEARNING_DIR = str(BASE_DIR / "learning_data")
LOG_FILE = str(BASE_DIR / "logs" / "memory_log.txt")
CONFIG_FILE = str(BASE_DIR / "config" / "memory_config.json")
DEFAULT_CONFIG = {
    "enabled": True,
    "max_short_term_memories": 100,
    "long_term_memory_threshold": 3,
    "memory_cleanup_days": 30,
    "learning_rate": 0.5
}

# Create directories if they don't exist
os.makedirs(os.path.dirname(MEMORY_DB), exist_ok=True)
os.makedirs(LEARNING_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class MemoryLearningPlugin:
    def __init__(self):
        self.config = self._load_config()
        self.core = None
        self.db_conn = None
        self.short_term_memory = []
        self.learned_patterns = defaultdict(Counter)
        self.learning_thread = None
        self.learning_running = False
        
        # Create learning directory if it doesn't exist
        if not os.path.exists(LEARNING_DIR):
            try:
                os.makedirs(LEARNING_DIR)
                logging.info(f"Created learning data directory")
            except Exception as e:
                logging.error(f"Failed to create learning directory: {str(e)}")
        
        # Initialize database
        self._initialize_database()
        
        logging.info("MemoryLearning plugin initialized")
    
    def _load_config(self):
        """Load configuration from file or create default"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading memory configuration: {str(e)}")
                return DEFAULT_CONFIG
        else:
            # Create default configuration
            try:
                os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
                with open(CONFIG_FILE, "w") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=2)
                logging.info("Created default memory configuration")
            except Exception as e:
                logging.error(f"Error creating default memory configuration: {str(e)}")
            
            return DEFAULT_CONFIG
    
    def _initialize_database(self):
        """Initialize the SQLite memory database"""
        try:
            self.db_conn = sqlite3.connect(MEMORY_DB, check_same_thread=False)
            cursor = self.db_conn.cursor()
            
            # Create memories table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                importance INTEGER DEFAULT 1,
                access_count INTEGER DEFAULT 1,
                last_accessed TEXT
            )
            ''')
            
            # Create associations table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS associations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id INTEGER,
                associated_with_id INTEGER,
                strength REAL DEFAULT 0.5,
                FOREIGN KEY (memory_id) REFERENCES memories(id),
                FOREIGN KEY (associated_with_id) REFERENCES memories(id)
            )
            ''')
            
            # Create learned patterns table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                occurrences INTEGER DEFAULT 1,
                last_observed TEXT
            )
            ''')
            
            self.db_conn.commit()
            logging.info("Memory database initialized")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize memory database: {str(e)}")
            return False
    
    def initialize(self, core):
        """Initialize the plugin with core system"""
        self.core = core
        logging.info("MemoryLearning plugin initialized with core system")
        
        # Start learning thread if enabled
        if self.config.get("enabled", True):
            self._start_learning_thread()
        
        return True
    
    def execute(self, command=None, core=None, **kwargs):
        """Execute plugin functionality based on command"""
        if core and not self.core:
            self.core = core
        
        if not command:
            return False
        
        # Memory-related commands
        if "remember this" in command.lower():
            memory_content = command.lower().split("remember this: ")[1]
            self._store_memory("user_instruction", memory_content, "direct_input", importance=2)
            return "I'll remember that."
        
        elif "what do you remember about" in command.lower():
            query = command.lower().split("what do you remember about ")[1]
            memories = self._recall_memories(query)
            return self._format_memories_response(memories)
        
        elif "forget about" in command.lower():
            topic = command.lower().split("forget about ")[1]
            count = self._forget_memories(topic)
            return f"I've removed {count} memories related to {topic}."
        
        elif "how many memories" in command.lower():
            return self._report_memory_stats()
        
        # Learning-related commands
        elif "what have you learned" in command.lower():
            if "about" in command.lower():
                topic = command.lower().split("what have you learned about ")[1]
                return self._report_learnings(topic)
            else:
                return self._report_learnings()
        
        elif "learn from" in command.lower():
            source = command.lower().split("learn from ")[1]
            result = self._learn_from_source(source)
            if result:
                return f"I've learned from {source}."
            else:
                return f"I couldn't learn from {source}."
        
        elif "test connection" in command.lower():
            return "Connection successful. Memory system is operational."
        
        return False
    
    def _format_memories_response(self, memories):
        """Format memories into a response string"""
        if not memories:
            return "I don't have any memories about that."
        
        response = f"I found {len(memories)} relevant memories:"
        
        for i, memory in enumerate(memories):
            # Format the timestamp for readability
            try:
                dt = datetime.datetime.fromisoformat(memory["timestamp"])
                time_str = dt.strftime("%B %d, %Y at %I:%M %p")
            except:
                time_str = memory["timestamp"]
            
            response += f"\n{i+1}. {memory['content']} (from {time_str})"
        
        return response
    
    def _start_learning_thread(self):
        """Start the background learning thread"""
        if self.learning_thread and self.learning_thread.is_alive():
            return
        
        self.learning_running = True
        self.learning_thread = threading.Thread(target=self._learning_loop)
        self.learning_thread.daemon = True
        self.learning_thread.start()
        logging.info("Learning thread started")
        return True
    
    def _stop_learning_thread(self):
        """Stop the background learning thread"""
        self.learning_running = False
        
        if self.learning_thread and self.learning_thread.is_alive():
            self.learning_thread.join(timeout=1.0)
        
        logging.info("Learning thread stopped")
        return True
    
    def _learning_loop(self):
        """Main learning thread that processes memories and identifies patterns"""
        while self.learning_running:
            try:
                # Process short-term memories for patterns
                self._process_short_term_memories()
                
                # Consolidate important short-term memories to long-term
                self._consolidate_memories()
                
                # Update associations between related memories
                self._update_associations()
                
                # Clean up old memories
                self._clean_old_memories()
                
                # Save learned patterns
                self._save_learned_patterns()
                
                # Wait before next learning cycle
                time.sleep(60)  # Run learning process every minute
                
            except Exception as e:
                logging.error(f"Error in learning loop: {str(e)}")
                time.sleep(300)  # Wait longer after an error
    
    def _store_memory(self, memory_type, content, source=None, importance=1):
        """Store a new memory in both short-term and database"""
        try:
            timestamp = datetime.datetime.now().isoformat()
            
            # Add to short-term memory
            memory = {
                "timestamp": timestamp,
                "type": memory_type,
                "content": content,
                "source": source,
                "importance": importance,
                "access_count": 1
            }
            
            self.short_term_memory.append(memory)
            
            # Limit short-term memory size
            max_memories = self.config.get("max_short_term_memories", 100)
            if len(self.short_term_memory) > max_memories:
                # Remove least important memories first
                self.short_term_memory.sort(key=lambda x: x["importance"])
                self.short_term_memory = self.short_term_memory[-max_memories:]
            
            # Store in database
            cursor = self.db_conn.cursor()
            cursor.execute('''
            INSERT INTO memories (timestamp, type, content, source, importance, access_count, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, memory_type, content, source, importance, 1, timestamp))
            
            self.db_conn.commit()
            memory_id = cursor.lastrowid
            
            logging.info(f"Stored new memory ID {memory_id}: {memory_type} - {content[:50]}...")
            return memory_id
            
        except Exception as e:
            logging.error(f"Failed to store memory: {str(e)}")
            return None
    
    def _recall_memories(self, query, limit=5):
        """Recall memories related to a query"""
        try:
            cursor = self.db_conn.cursor()
            
            # Search in memory content with relevance ranking
            cursor.execute('''
            SELECT id, timestamp, type, content, source, importance, access_count
            FROM memories
            WHERE content LIKE ?
            ORDER BY importance DESC, access_count DESC
            LIMIT ?
            ''', (f'%{query}%', limit))
            
            memories = cursor.fetchall()
            
            # Update access count for recalled memories
            now = datetime.datetime.now().isoformat()
            for memory in memories:
                memory_id = memory[0]
                cursor.execute('''
                UPDATE memories
                SET access_count = access_count + 1, last_accessed = ?
                WHERE id = ?
                ''', (now, memory_id))
            
            self.db_conn.commit()
            
            # Format results
            results = []
            for memory in memories:
                results.append({
                    "id": memory[0],
                    "timestamp": memory[1],
                    "type": memory[2],
                    "content": memory[3],
                    "source": memory[4],
                    "importance": memory[5],
                    "access_count": memory[6] + 1  # Include the current access
                })
            
            logging.info(f"Recalled {len(results)} memories for query: {query}")
            return results
            
        except Exception as e:
            logging.error(f"Failed to recall memories: {str(e)}")
            return []
    
    def _report_memories(self, memories):
        """Report recalled memories to the user"""
        if not memories:
            return "I don't have any memories about that."
        
        response = f"I found {len(memories)} relevant memories:"
        
        for i, memory in enumerate(memories):
            # Format the timestamp for readability
            try:
                dt = datetime.datetime.fromisoformat(memory["timestamp"])
                time_str = dt.strftime("%B %d, %Y at %I:%M %p")
            except:
                time_str = memory["timestamp"]
            
            response += f"\n{i+1}. {memory['content']} (from {time_str})"
        
        return response
    
    def _forget_memories(self, topic):
        """Remove memories related to a specific topic"""
        try:
            cursor = self.db_conn.cursor()
            
            # Find relevant memories
            cursor.execute('''
            SELECT id FROM memories
            WHERE content LIKE ?
            ''', (f'%{topic}%',))
            
            memory_ids = [row[0] for row in cursor.fetchall()]
            
            if not memory_ids:
                logging.info(f"No memories found to forget about: {topic}")
                return 0
            
            # Delete from associations
            cursor.execute('''
            DELETE FROM associations
            WHERE memory_id IN ({}) OR associated_with_id IN ({})
            '''.format(','.join(['?']*len(memory_ids)), ','.join(['?']*len(memory_ids))), 
            memory_ids + memory_ids)
            
            # Delete from memories
            cursor.execute('''
            DELETE FROM memories
            WHERE id IN ({})
            '''.format(','.join(['?']*len(memory_ids))), memory_ids)
            
            # Also remove from short-term memory
            self.short_term_memory = [m for m in self.short_term_memory 
                                     if topic.lower() not in m["content"].lower()]
            
            self.db_conn.commit()
            
            logging.info(f"Forgot {len(memory_ids)} memories about: {topic}")
            return len(memory_ids)
            
        except Exception as e:
            logging.error(f"Failed to forget memories: {str(e)}")
            return 0
    
    def _report_memory_stats(self):
        """Report statistics about stored memories"""
        try:
            cursor = self.db_conn.cursor()
            
            # Get total count
            cursor.execute('SELECT COUNT(*) FROM memories')
            total_count = cursor.fetchone()[0]
            
            # Get count by type
            cursor.execute('SELECT type, COUNT(*) FROM memories GROUP BY type')
            type_counts = cursor.fetchall()
            
            # Get most accessed memories
            cursor.execute('''
            SELECT content, access_count FROM memories
            ORDER BY access_count DESC LIMIT 3
            ''')
            most_accessed = cursor.fetchall()
            
            response = f"I have {total_count} memories stored. "
            
            if type_counts:
                response += "By type: "
                for type_info in type_counts:
                    response += f"{type_info[0]}: {type_info[1]}, "
                response = response[:-2] + ". "
            
            if most_accessed:
                response += "Most frequently accessed: "
                for mem in most_accessed:
                    # Truncate long memories
                    content = mem[0]
                    if len(content) > 30:
                        content = content[:27] + "..."
                    response += f'"{content}" ({mem[1]} times), '
                response = response[:-2] + "."
            
            logging.info("Reported memory statistics to user")
            return response
            
        except Exception as e:
            logging.error(f"Failed to report memory stats: {str(e)}")
            return "I'm having trouble accessing my memory statistics."
    
    def _process_short_term_memories(self):
        """Process short-term memories to identify patterns"""
        try:
            if not self.short_term_memory:
                return
            
            # Extract information to learn from
            for memory in self.short_term_memory:
                content = memory["content"]
                memory_type = memory["type"]
                
                # Learn from content based on type
                if memory_type == "user_command":
                    # Learn command patterns
                    self.learned_patterns["commands"][content] += 1
                    
                    # Extract keywords
                    words = content.lower().split()
                    for word in words:
                        if len(word) > 3:  # Ignore very short words
                            self.learned_patterns["command_keywords"][word] += 1
                
                elif memory_type == "observation":
                    # Learn from observations
                    self.learned_patterns["observations"][content] += 1
                
                elif memory_type == "system_event":
                    # Learn from system events
                    self.learned_patterns["system_events"][content] += 1
            
            logging.info(f"Processed {len(self.short_term_memory)} short-term memories for patterns")
            
        except Exception as e:
            logging.error(f"Error processing short-term memories: {str(e)}")
    
    def _consolidate_memories(self):
        """Consolidate important short-term memories into long-term memory"""
        try:
            # Identify memories for consolidation based on importance or repetition
            threshold = self.config.get("long_term_memory_threshold", 3)
            
            # Count occurrences of similar memories
            content_count = Counter()
            for memory in self.short_term_memory:
                content_count[memory["content"]] += 1
            
            for memory in self.short_term_memory[:]:
                # Memories are consolidated if they are important or repeated
                if (memory["importance"] >= threshold or 
                    content_count[memory["content"]] >= threshold):
                    
                    # Check if already in long-term memory
                    cursor = self.db_conn.cursor()
                    cursor.execute('''
                    SELECT id FROM memories 
                    WHERE content = ? AND type = ?
                    ''', (memory["content"], memory["type"]))
                    
                    existing = cursor.fetchone()
                    if existing:
                        # Update importance and access count
                        memory_id = existing[0]
                        cursor.execute('''
                        UPDATE memories
                        SET importance = importance + 1, access_count = access_count + 1
                        WHERE id = ?
                        ''', (memory_id,))
                    else:
                        # New consolidated memory with increased importance
                        cursor.execute('''
                        INSERT INTO memories 
                        (timestamp, type, content, source, importance, access_count, last_accessed)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            memory["timestamp"],
                            memory["type"],
                            memory["content"],
                            memory["source"],
                            memory["importance"] + 1,  # Increase importance
                            memory["access_count"],
                            datetime.datetime.now().isoformat()
                        ))
                    
                    self.db_conn.commit()
                    # Remove from short-term memory
                    self.short_term_memory.remove(memory)
            
            logging.info("Memory consolidation completed")
            
        except Exception as e:
            logging.error(f"Error consolidating memories: {str(e)}")
    
    def _update_associations(self):
        """Update associations between related memories"""
        try:
            cursor = self.db_conn.cursor()
            
            # Get all memories
            cursor.execute('SELECT id, content FROM memories')
            memories = cursor.fetchall()
            
            # Find and update associations (simplified approach)
            for i, mem1 in enumerate(memories):
                id1, content1 = mem1
                words1 = set(content1.lower().split())
                
                for mem2 in memories[i+1:]:
                    id2, content2 = mem2
                    words2 = set(content2.lower().split())
                    
                    # Calculate simple similarity
                    common_words = words1.intersection(words2)
                    if common_words:
                        similarity = len(common_words) / max(len(words1), len(words2))
                        
                        if similarity > 0.2:  # Only associate if there's meaningful similarity
                            # Check if association already exists
                            cursor.execute('''
                            SELECT id, strength FROM associations
                            WHERE (memory_id = ? AND associated_with_id = ?) 
                               OR (memory_id = ? AND associated_with_id = ?)
                            ''', (id1, id2, id2, id1))
                            
                            existing = cursor.fetchone()
                            if existing:
                                # Update strength of existing association
                                assoc_id, strength = existing
                                new_strength = min(1.0, strength + 0.1)  # Increase strength, max 1.0
                                
                                cursor.execute('''
                                UPDATE associations
                                SET strength = ?
                                WHERE id = ?
                                ''', (new_strength, assoc_id))
                            else:
                                # Create new association
                                cursor.execute('''
                                INSERT INTO associations (memory_id, associated_with_id, strength)
                                VALUES (?, ?, ?)
                                ''', (id1, id2, similarity))
            
            self.db_conn.commit()
            logging.info("Memory associations updated")
            
        except Exception as e:
            logging.error(f"Error updating memory associations: {str(e)}")
    
    def _clean_old_memories(self):
        """Clean up old memories based on configuration"""
        try:
            days = self.config.get("memory_cleanup_days", 30)
            cutoff_date = (datetime.datetime.now() - 
                          datetime.timedelta(days=days)).isoformat()
            
            cursor = self.db_conn.cursor()
            
            # Find old, low-importance, rarely accessed memories
            cursor.execute('''
            SELECT id FROM memories
            WHERE timestamp < ? AND importance <= 1 AND access_count <= 2
            ''', (cutoff_date,))
            
            old_memory_ids = [row[0] for row in cursor.fetchall()]
            
            if old_memory_ids:
                # Delete associations
                cursor.execute('''
                DELETE FROM associations
                WHERE memory_id IN ({}) OR associated_with_id IN ({})
                '''.format(','.join(['?']*len(old_memory_ids)), ','.join(['?']*len(old_memory_ids))), 
                old_memory_ids + old_memory_ids)
                
                # Delete memories
                cursor.execute('''
                DELETE FROM memories
                WHERE id IN ({})
                '''.format(','.join(['?']*len(old_memory_ids))), old_memory_ids)
                
                self.db_conn.commit()
                logging.info(f"Cleaned up {len(old_memory_ids)} old memories")
            
        except Exception as e:
            logging.error(f"Error cleaning old memories: {str(e)}")
    
    def _save_learned_patterns(self):
        """Save learned patterns to database and files"""
        try:
            cursor = self.db_conn.cursor()
            now = datetime.datetime.now().isoformat()
            
            # Update patterns in database
            for pattern_type, patterns in self.learned_patterns.items():
                for pattern_data, occurrences in patterns.items():
                    # Check if pattern already exists
                    cursor.execute('''
                    SELECT id, occurrences FROM patterns
                    WHERE pattern_type = ? AND pattern_data = ?
                    ''', (pattern_type, pattern_data))
                    
                    existing = cursor.fetchone()
                    if existing:
                        # Update existing pattern
                        pattern_id, existing_count = existing
                        cursor.execute('''
                        UPDATE patterns
                        SET occurrences = ?, last_observed = ?
                        WHERE id = ?
                        ''', (existing_count + occurrences, now, pattern_id))
                    else:
                        # Insert new pattern
                        cursor.execute('''
                        INSERT INTO patterns (pattern_type, pattern_data, occurrences, last_observed)
                        VALUES (?, ?, ?, ?)
                        ''', (pattern_type, pattern_data, occurrences, now))
            
            self.db_conn.commit()
            
            # Save to JSON file for easier analysis
            patterns_file = os.path.join(LEARNING_DIR, "learned_patterns.json")
            with open(patterns_file, "w") as f:
                # Convert Counter objects to dictionaries for JSON serialization
                serializable_patterns = {}
                for pattern_type, counter in self.learned_patterns.items():
                    serializable_patterns[pattern_type] = dict(counter)
                
                json.dump(serializable_patterns, f, indent=2)
            
            logging.info("Saved learned patterns")
            
        except Exception as e:
            logging.error(f"Error saving learned patterns: {str(e)}")
    
    def _report_learnings(self, topic=None):
        """Report what the system has learned, optionally filtered by topic"""
        try:
            cursor = self.db_conn.cursor()
            
            if topic:
                # Get patterns related to the topic
                cursor.execute('''
                SELECT pattern_type, pattern_data, occurrences 
                FROM patterns
                WHERE pattern_data LIKE ?
                ORDER BY occurrences DESC
                LIMIT 10
                ''', (f'%{topic}%',))
            else:
                # Get most common patterns of each type
                cursor.execute('''
                SELECT pattern_type, pattern_data, occurrences 
                FROM patterns
                ORDER BY occurrences DESC
                LIMIT 10
                ''')
            
            patterns = cursor.fetchall()
            
            if not patterns:
                return f"I haven't learned anything{' about ' + topic if topic else ''} yet."
            
            response = f"Here's what I've learned{' about ' + topic if topic else ''}:"
            
            # Group by pattern type
            by_type = defaultdict(list)
            for pattern in patterns:
                by_type[pattern[0]].append((pattern[1], pattern[2]))
            
            for pattern_type, items in by_type.items():
                response += f"\n{pattern_type.title()}: "
                for item, count in items[:3]:  # Limit to top 3 per type
                    response += f"{item} ({count} times), "
                response = response[:-2]
            
            logging.info(f"Reported learning patterns to user")
            return response
            
        except Exception as e:
            logging.error(f"Error reporting learnings: {str(e)}")
            return "I'm having trouble accessing my learning data."
    
    def _learn_from_source(self, source):
        """Learn from a specified source (file, conversation, etc.)"""
        try:
            if source.lower() == "conversation":
                # This would process conversation history
                # For demonstration, we'll just add a sample memory
                self._store_memory(
                    "observation", 
                    "Learning from conversation history is valuable for improving responses",
                    "conversation_analysis",
                    importance=2
                )
                return True
                
            elif source.lower() == "screen":
                # This would integrate with the vision plugin
                # For demonstration, we'll just add a sample memory
                self._store_memory(
                    "observation",
                    "Screen interfaces typically have consistent navigation elements",
                    "screen_analysis",
                    importance=2
                )
                return True
                
            elif os.path.exists(source):
                # For demonstration, we'll just add a sample memory
                self._store_memory(
                    "observation",
                    f"File {source} contains information that can be processed for learning",
                    "file_analysis",
                    importance=2
                )
                return True
                
            else:
                return False
                
        except Exception as e:
            logging.error(f"Error learning from source {source}: {str(e)}")
            return False
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
            logging.info("Memory configuration saved")
            return True
        except Exception as e:
            logging.error(f"Failed to save memory configuration: {str(e)}")
            return False
    
    def shutdown(self):
        """Clean shutdown of the plugin"""
        self._stop_learning_thread()
        self._save_config()
        self._save_learned_patterns()
        
        if self.db_conn:
            self.db_conn.close()
            
        logging.info("MemoryLearning plugin shutdown")

# Plugin entry points for the plugin system
def initialize(core):
    """Initialize the plugin - required by the plugin system"""
    global plugin_instance
    plugin_instance = MemoryLearningPlugin()
    return plugin_instance.initialize(core)

def execute(**kwargs):
    """Execute plugin functionality - required by the plugin system"""
    global plugin_instance
    if not plugin_instance:
        plugin_instance = MemoryLearningPlugin()
    return plugin_instance.execute(**kwargs)

# Global plugin instance
plugin_instance = None

# For standalone testing
if __name__ == "__main__":
    print("Memory Learning plugin testing mode")
    
    plugin = MemoryLearningPlugin()
    
    # Test memory storage
    print("\nTesting memory storage...")
    plugin._store_memory("test", "This is a test memory", "test_script", 1)
    
    # Test memory recall
    print("\nTesting memory recall...")
    memories = plugin._recall_memories("test")
    for memory in memories:
        print(f"Recalled: {memory['content']}")
    
    print("\nTest complete") 