#!/usr/bin/env python3
"""
Direct Chat Interface for SassyQueenCore
Allows direct interaction with loaded GGUF models
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                            QLabel, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from model_loader import ModelLoader

class DirectChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model_loader = ModelLoader()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("SassyQueenCore Direct Chat")
        self.setMinimumSize(800, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Model loading section
        model_frame = QWidget()
        model_layout = QHBoxLayout(model_frame)
        
        self.model_path = QLineEdit()
        self.model_path.setPlaceholderText("Select GGUF model...")
        model_layout.addWidget(self.model_path)
        
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_model)
        model_layout.addWidget(browse_button)
        
        load_button = QPushButton("Load Model")
        load_button.clicked.connect(self.load_model)
        model_layout.addWidget(load_button)
        
        layout.addWidget(model_frame)
        
        # Model status
        self.status_label = QLabel("No model loaded")
        layout.addWidget(self.status_label)
        
        # Chat history
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        layout.addWidget(self.chat_history)
        
        # Input area
        input_frame = QWidget()
        input_layout = QHBoxLayout(input_frame)
        
        self.message_input = QLineEdit()
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)
        input_layout.addWidget(send_button)
        
        layout.addWidget(input_frame)
        
    def browse_model(self):
        """Browse for a GGUF model file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select GGUF Model",
            "",
            "GGUF Models (*.gguf);;All Files (*.*)"
        )
        if file_path:
            self.model_path.setText(file_path)
            
    def load_model(self):
        """Load the selected model"""
        model_path = self.model_path.text().strip()
        if not model_path:
            QMessageBox.warning(self, "Error", "Please select a model file")
            return
            
        try:
            self.status_label.setText("Loading model...")
            QApplication.processEvents()
            
            model = self.model_loader.load_model(model_path)
            self.status_label.setText(f"Model loaded: {model['name']}")
            
            self.append_to_chat("System", "Model loaded successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load model: {str(e)}")
            self.status_label.setText("Model loading failed")
            
    def send_message(self):
        """Send a message to the model"""
        if not self.model_loader.get_model_info():
            QMessageBox.warning(self, "Error", "Please load a model first")
            return
            
        message = self.message_input.text().strip()
        if not message:
            return
            
        self.message_input.clear()
        self.append_to_chat("You", message)
        
        try:
            response = self.model_loader.process_message(message)
            self.append_to_chat("Model", response)
            
        except Exception as e:
            self.append_to_chat("System", f"Error: {str(e)}")
            
    def append_to_chat(self, sender, message):
        """Append a message to the chat history"""
        self.chat_history.append(f"<b>{sender}:</b> {message}")
        
def main():
    app = QApplication(sys.argv)
    window = DirectChatWindow()
    window.show()
    sys.exit(app.exec())
