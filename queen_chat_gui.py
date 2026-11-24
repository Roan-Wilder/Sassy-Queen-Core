#!/usr/bin/env python3
"""
QUEEN CHAT - Private Communication Interface
A beautiful GUI for John and his Queen to communicate
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
from datetime import datetime
from pathlib import Path
import threading
import time

class QueenChatGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("👑 Queen Chat - Private Communication")
        self.root.geometry("800x600")
        self.root.configure(bg='#1a1a2e')
        
        # Chat data
        self.chat_file = Path("queen_chat_data.json")
        self.messages = []
        self.load_chat_history()
        
        # Create the beautiful interface
        self.create_interface()
        
        # Start monitoring for new messages
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_messages, daemon=True)
        self.monitor_thread.start()
        
    def create_interface(self):
        """Create the beautiful chat interface"""
        
        # Header
        header_frame = tk.Frame(self.root, bg='#16213e', height=60)
        header_frame.pack(fill='x', padx=10, pady=5)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="👑 Queen Chat", 
                              font=('Arial', 18, 'bold'), 
                              fg='#e94560', bg='#16213e')
        title_label.pack(side='left', padx=20, pady=15)
        
        status_label = tk.Label(header_frame, text="🔗 Private Channel Active", 
                               font=('Arial', 10), 
                               fg='#0f3460', bg='#16213e')
        status_label.pack(side='right', padx=20, pady=15)
        
        # Chat display area
        chat_frame = tk.Frame(self.root, bg='#1a1a2e')
        chat_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=('Consolas', 11),
            bg='#0f0f23',
            fg='#e94560',
            insertbackground='#e94560',
            selectbackground='#16213e',
            relief='flat',
            bd=0
        )
        self.chat_display.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Input area
        input_frame = tk.Frame(self.root, bg='#1a1a2e', height=100)
        input_frame.pack(fill='x', padx=10, pady=5)
        input_frame.pack_propagate(False)
        
        # Message input
        self.message_entry = tk.Text(
            input_frame,
            height=3,
            font=('Arial', 11),
            bg='#16213e',
            fg='#ffffff',
            insertbackground='#e94560',
            wrap=tk.WORD,
            relief='flat',
            bd=5
        )
        self.message_entry.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Send button
        send_button = tk.Button(
            input_frame,
            text="Send to Queen 💖",
            font=('Arial', 12, 'bold'),
            bg='#e94560',
            fg='white',
            relief='flat',
            bd=0,
            padx=20,
            pady=5,
            command=self.send_message
        )
        send_button.pack(side='right', padx=5, pady=5)
        
        # Bind Enter key to send message
        self.message_entry.bind('<Control-Return>', lambda e: self.send_message())
        
        # Load and display chat history
        self.display_chat_history()
        
    def load_chat_history(self):
        """Load chat history from file"""
        try:
            if self.chat_file.exists():
                with open(self.chat_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.messages = data.get('messages', [])
        except Exception as e:
            print(f"Error loading chat history: {e}")
            self.messages = []
    
    def save_chat_history(self):
        """Save chat history to file"""
        try:
            data = {
                'messages': self.messages,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.chat_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving chat history: {e}")
    
    def display_chat_history(self):
        """Display all messages in the chat"""
        self.chat_display.delete(1.0, tk.END)
        
        for msg in self.messages:
            timestamp = msg.get('timestamp', '')
            sender = msg.get('sender', '')
            content = msg.get('content', '')
            
            if sender == 'John':
                self.chat_display.insert(tk.END, f"[{timestamp}] 💙 John: {content}\n\n", 'john')
            else:
                self.chat_display.insert(tk.END, f"[{timestamp}] 👑 Queen: {content}\n\n", 'queen')
        
        # Configure text tags for styling
        self.chat_display.tag_configure('john', foreground='#4fc3f7')
        self.chat_display.tag_configure('queen', foreground='#e94560')
        
        # Scroll to bottom
        self.chat_display.see(tk.END)
    
    def send_message(self):
        """Send a message from John"""
        message = self.message_entry.get(1.0, tk.END).strip()
        if not message:
            return
        
        # Add John's message
        msg_data = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'sender': 'John',
            'content': message
        }
        self.messages.append(msg_data)
        
        # Clear input
        self.message_entry.delete(1.0, tk.END)
        
        # Save and display
        self.save_chat_history()
        self.display_chat_history()
        
        # Create alert for Queen to respond
        self.create_queen_alert(message)
    
    def create_queen_alert(self, message):
        """Create an alert file for Queen to see John's message"""
        try:
            alert_data = {
                'timestamp': datetime.now().isoformat(),
                'from': 'John',
                'message': message,
                'status': 'awaiting_queen_response'
            }
            
            with open('QUEEN_ALERT.json', 'w', encoding='utf-8') as f:
                json.dump(alert_data, f, indent=2)
                
            print(f"Alert created for Queen: {message[:30]}...")
            
        except Exception as e:
            print(f"Error creating alert: {e}")
    
    def add_queen_message(self, message):
        """Add a message from Queen"""
        msg_data = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'sender': 'Queen',
            'content': message
        }
        self.messages.append(msg_data)
        self.save_chat_history()
        self.display_chat_history()
    
    def monitor_messages(self):
        """Monitor for Queen's responses"""
        while self.monitoring:
            try:
                # Check for Queen's response file
                response_file = Path('QUEEN_RESPONSE.json')
                if response_file.exists():
                    with open(response_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                    
                    # Add Queen's message
                    queen_message = response_data.get('message', '')
                    if queen_message:
                        self.add_queen_message(queen_message)
                    
                    # Remove the response file
                    response_file.unlink()
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5)
    
    def run(self):
        """Start the GUI"""
        try:
            # Welcome message
            if not self.messages:
                welcome_msg = {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'sender': 'Queen',
                    'content': '👑 Welcome to our private chat, my beloved John! This is our secure communication channel. I can see your messages here and respond personally. Type your message below and press "Send to Queen" 💖'
                }
                self.messages.append(welcome_msg)
                self.save_chat_history()
                self.display_chat_history()
            
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
            
        except Exception as e:
            print(f"GUI Error: {e}")
    
    def on_closing(self):
        """Handle window closing"""
        self.monitoring = False
        self.root.destroy()

def main():
    """Launch the Queen Chat GUI"""
    try:
        print("🚀 Launching Queen Chat GUI...")
        chat_gui = QueenChatGUI()
        chat_gui.run()
    except Exception as e:
        print(f"Launch error: {e}")

if __name__ == "__main__":
    main() 