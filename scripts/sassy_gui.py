#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add parent directory to path to ensure imports work correctly
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                            QLabel, QTabWidget, QScrollArea, QFrame, QMessageBox,
                            QComboBox, QSlider, QCheckBox, QSpinBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor
import json
import logging
from datetime import datetime

# Set up logging
log_dir = parent_dir / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    filename=str(log_dir / "sassy_gui.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SassyGUI(QMainWindow):
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.setup_ui()
        self.load_theme()
        
        # Load saved settings
        self.load_soul_settings()
        self.load_integration_settings()
        self.load_gguf_settings()
        
        logging.info("SassyGUI initialized")
        # Holders for locally loaded models
        self.llm_instance = None  # llama.cpp GGUF
        self.hf_model = None      # Hugging Face PyTorch model
        self.hf_tokenizer = None
        
    def load_gguf_model(self):
        """Load a GGUF model file with workspace-relative path"""
        try:
            # Construct path relative to current workspace
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "llm", "codellama-7b.gguf")
            
            if not os.path.exists(file_path):
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Model file not found: {file_path}\nPlease verify the path is correct."
                )
                return
                
            # Show loading message
            self.model_path_label.setText("Loading model... Please wait...")
            self.model_path_label.setStyleSheet("color: orange;")
            QApplication.processEvents()  # Update UI
            
            try:
                from llama_cpp import Llama
                
                # Adjust configuration parameters for safer defaults
                model_config = {
                    'model_path': str(file_path),
                    'n_ctx': 1024,         # Reduced context size
                    'n_batch': 128,        # Smaller batch size
                    'n_threads': 2,        # Minimal threads
                    'n_gpu_layers': 0,     # CPU-only mode
                    'vocab_only': False,
                    'use_mmap': True,
                    'use_mlock': False,    # Don't lock memory
                }

                # Log configuration for debugging
                logging.info(f"Loading model with configuration: {model_config}")

                # Attempt to load the model
                self.llm_instance = Llama(**model_config)

                # Log success
                logging.info(f"Model loaded successfully: {file_path}")

                # Update UI with success
                model_name = os.path.basename(file_path)
                self.model_selection.addItem(model_name)
                self.model_selection.setCurrentText(model_name)
                self.model_path_label.setText(f"Loaded: {file_path}")
                self.model_path_label.setStyleSheet("color: green;")
                
                # Store the model path
                self.current_model_path = file_path
                
                # Update API type to Local
                self.api_type.setCurrentText("Local (Ollama)")
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Model Loaded Successfully",
                    f"Model: {model_name}\nPath: {file_path}"
                )
                
                # Update the chat interface
                self.add_to_chat("System", f"GGUF model '{model_name}' loaded and ready!")
                
            except ImportError:
                QMessageBox.critical(
                    self,
                    "Missing Dependency",
                    "The llama-cpp-python package is required. Please install it using:\npip install llama-cpp-python"
                )
                return
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error Loading Model",
                    f"Failed to load model: {str(e)}\n\nPlease check that the model file is valid."
                )
                logging.error(f"Failed to load GGUF model: {str(e)}")
                self.model_path_label.setText("Error loading model")
                self.model_path_label.setStyleSheet("color: red;")
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An unexpected error occurred: {str(e)}"
            )
            logging.error(f"Unexpected error in load_gguf_model: {str(e)}")

    def load_local_model(self):
        """Browse and load a local model file (.gguf, .pt, .bin, .safetensors)."""
        from PyQt6.QtWidgets import QFileDialog
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Local Model",
                "",
                "Models (*.gguf *.pt *.bin *.safetensors);;All Files (*)"
            )
            if not file_path:
                return
            self.model_path_label.setText("Loading model... Please wait...")
            self.model_path_label.setStyleSheet("color: orange;")
            QApplication.processEvents()
            self._load_model_from_path(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open model: {str(e)}")
            logging.error(f"Error in load_local_model: {str(e)}")

    def _load_model_from_path(self, file_path: str):
        """Load a model depending on file extension."""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".gguf":
                # Use llama.cpp
                try:
                    from llama_cpp import Llama
                except ImportError:
                    QMessageBox.critical(
                        self,
                        "Missing Dependency",
                        "The llama-cpp-python package is required. Please install it using:\n\n"
                        "pip install llama-cpp-python"
                    )
                    return

                # Get settings from UI (Settings tab) or config file
                n_gpu_layers = 0
                n_ctx = 2048
                n_batch = 512
                n_threads = 4
                use_mmap = False
                gpu_enabled = False
                
                try:
                    # Try to get settings from UI first
                    if hasattr(self, 'gpu_layers_spin'):
                        n_gpu_layers = self.gpu_layers_spin.value()
                        n_ctx = int(self.ctx_size_combo.currentText())
                        n_batch = int(self.batch_size_combo.currentText())
                        n_threads = self.cpu_threads_spin.value()
                        use_mmap = self.use_mmap_check.isChecked()
                        gpu_enabled = n_gpu_layers != 0
                        logging.info(f"Using UI settings: GPU layers={n_gpu_layers}, ctx={n_ctx}, batch={n_batch}, threads={n_threads}, mmap={use_mmap}")
                    else:
                        # Fall back to config file
                        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
                        config_file = os.path.join(config_dir, "llm_config.json")
                        if os.path.exists(config_file):
                            with open(config_file, 'r') as f:
                                llm_config = json.load(f)
                            n_gpu_layers = llm_config.get("n_gpu_layers", 0)
                            n_ctx = llm_config.get("n_ctx", 2048)
                            n_batch = llm_config.get("n_batch", 512)
                            n_threads = llm_config.get("n_threads", 4)
                            use_mmap = llm_config.get("use_mmap", False)
                            gpu_enabled = n_gpu_layers != 0
                            logging.info(f"Using config file settings")
                except Exception as e:
                    logging.warning(f"Could not load settings: {str(e)}, using defaults")

                # Show loading status
                self.model_path_label.setText("Loading GGUF model... Please wait...")
                self.model_path_label.setStyleSheet("color: orange;")
                QApplication.processEvents()

                # Verify file exists and is readable
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Model file not found: {file_path}")
                
                file_size = os.path.getsize(file_path)
                if file_size < 1000:  # Less than 1KB is likely not a valid model
                    raise ValueError(f"Model file appears too small ({file_size} bytes). May be corrupted.")
                
                logging.info(f"GGUF file size: {file_size / (1024*1024):.1f} MB")

                model_config = {
                    'model_path': str(file_path),
                    'n_ctx': n_ctx,
                    'n_batch': n_batch,
                    'n_threads': n_threads,
                    'n_gpu_layers': n_gpu_layers,
                    'vocab_only': False,
                    'use_mmap': use_mmap,
                    'use_mlock': False,
                    'verbose': False,
                }
                
                logging.info(f"Loading GGUF via llama.cpp: {model_config}")
                
                load_attempts = [
                    # Attempt 1: User's settings
                    model_config.copy(),
                    # Attempt 2: Same but CPU only
                    {**model_config, 'n_gpu_layers': 0},
                    # Attempt 3: Conservative settings (reduced context and batch)
                    {
                        'model_path': str(file_path),
                        'n_ctx': min(n_ctx, 1024),
                        'n_batch': min(n_batch, 256),
                        'n_threads': n_threads,
                        'n_gpu_layers': 0,
                        'use_mmap': False,
                        'use_mlock': False,
                        'verbose': False,
                    },
                    # Attempt 4: Minimal config
                    {
                        'model_path': str(file_path),
                        'n_ctx': 512,
                        'n_batch': 64,
                        'n_threads': 2,
                        'n_gpu_layers': 0,
                        'use_mmap': False,
                        'use_mlock': False,
                        'verbose': False,
                    },
                ]
                
                last_error = None
                for attempt_num, config in enumerate(load_attempts, 1):
                    try:
                        logging.info(f"Load attempt {attempt_num}: {config}")
                        self.llm_instance = Llama(**config)
                        gpu_enabled = config.get('n_gpu_layers', 0) != 0
                        logging.info(f"Successfully loaded on attempt {attempt_num}")
                        break
                    except Exception as load_error:
                        last_error = load_error
                        error_str = str(load_error)
                        logging.warning(f"Attempt {attempt_num} failed: {error_str}")
                        
                        # If it's an access violation, the library might be broken
                        if "access violation" in error_str.lower():
                            logging.error("Access violation detected - llama-cpp-python may need reinstalling")
                        
                        if attempt_num == len(load_attempts):
                            # All attempts failed
                            raise RuntimeError(
                                f"Failed to load model after {len(load_attempts)} attempts.\n"
                                f"Last error: {error_str}\n\n"
                                f"Try reinstalling llama-cpp-python:\n"
                                f"pip uninstall llama-cpp-python -y\n"
                                f"pip install llama-cpp-python --no-cache-dir"
                            ) from last_error
                
                self.hf_model = None
                self.hf_tokenizer = None
                model_name = os.path.basename(file_path)
                if self.model_selection.findText(model_name) == -1:
                    self.model_selection.addItem(model_name)
                self.model_selection.setCurrentText(model_name)
                self.model_path_label.setText(f"Loaded: {file_path}")
                self.model_path_label.setStyleSheet("color: green;")
                self.api_type.setCurrentText("Local (Ollama)")
                
                gpu_status = " (GPU accelerated)" if gpu_enabled and n_gpu_layers != 0 else " (CPU)"
                self.add_to_chat("System", f"Local GGUF model '{model_name}' loaded{gpu_status}!")
                
                if gpu_enabled and n_gpu_layers != 0:
                    QMessageBox.information(
                        self, 
                        "Model Loaded with GPU",
                        f"Model: {model_name}\n\nGPU Acceleration: Enabled\nGPU Layers: {n_gpu_layers if n_gpu_layers > 0 else 'All'}"
                    )
                return

            # PyTorch/Transformers: .pt/.bin/.safetensors
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer
            except ImportError:
                QMessageBox.critical(
                    self,
                    "Missing Dependency",
                    "PyTorch/Transformers required. Please install:\n\n"
                    "pip install torch transformers safetensors"
                )
                return

            model_dir = os.path.dirname(file_path)
            load_path = model_dir if os.path.exists(os.path.join(model_dir, 'config.json')) else file_path

            # Check available system memory before loading
            try:
                import psutil
                available_memory_gb = psutil.virtual_memory().available / (1024**3)
                
                # Estimate model size from safetensors files
                model_size_bytes = 0
                if os.path.isdir(load_path):
                    for f in os.listdir(load_path):
                        if f.endswith('.safetensors') or f.endswith('.bin'):
                            model_size_bytes += os.path.getsize(os.path.join(load_path, f))
                estimated_size_gb = model_size_bytes / (1024**3)
                # Loading requires roughly 2x model size for overhead
                required_memory_gb = estimated_size_gb * 2.5
                
                logging.info(f"Available memory: {available_memory_gb:.1f}GB, Model size: {estimated_size_gb:.1f}GB, Required: {required_memory_gb:.1f}GB")
                
                if available_memory_gb < required_memory_gb:
                    QMessageBox.warning(
                        self,
                        "Insufficient Memory",
                        f"This model requires approximately {required_memory_gb:.1f}GB of RAM to load.\n\n"
                        f"Your system currently has {available_memory_gb:.1f}GB available.\n\n"
                        "Options:\n"
                        "1. Close other applications to free memory\n"
                        "2. Use a smaller quantized model (GGUF format)\n"
                        "3. Use Ollama which handles memory more efficiently\n\n"
                        "Attempting to load anyway (may crash)..."
                    )
            except ImportError:
                logging.warning("psutil not available for memory check")

            # Check for available GPU backends
            device = "cpu"
            gpu_backend = None
            
            if torch.cuda.is_available():
                device = "cuda"
                gpu_backend = "CUDA"
            else:
                # Try DirectML for AMD GPUs
                try:
                    import torch_directml
                    device = torch_directml.device()
                    gpu_backend = "DirectML"
                    logging.info("DirectML device available - using AMD GPU!")
                except ImportError:
                    logging.info("DirectML not available, using CPU")
                except Exception as e:
                    logging.warning(f"DirectML error: {str(e)}, falling back to CPU")
            
            # Set dtype based on device
            if gpu_backend:
                dtype = torch.float16
            else:
                # Try bfloat16 first (better precision), fall back to float16
                dtype = torch.bfloat16 if hasattr(torch, 'bfloat16') else torch.float16

            device_info = f"{device}" if not gpu_backend else f"{gpu_backend}"
            logging.info(f"Loading HF model from {load_path} on {device_info} ({dtype})")
            
            # Update UI to show loading progress
            self.model_path_label.setText("Loading model... This may take several minutes...")
            self.model_path_label.setStyleSheet("color: orange;")
            QApplication.processEvents()
            
            try:
                tokenizer = AutoTokenizer.from_pretrained(load_path, use_fast=True)
                model = AutoModelForCausalLM.from_pretrained(
                    load_path,
                    torch_dtype=dtype,  # Note: newer transformers uses 'dtype' but torch_dtype still works
                    low_cpu_mem_usage=True,
                    device_map="auto" if torch.cuda.is_available() else None,
                )
                if not torch.cuda.is_available():
                    model.to(device)
            except Exception as load_error:
                error_msg = str(load_error)
                logging.error(f"Model loading failed: {error_msg}")
                
                # Check if it's a memory error
                if "out of memory" in error_msg.lower() or "cannot allocate" in error_msg.lower():
                    QMessageBox.critical(
                        self,
                        "Out of Memory",
                        f"Failed to load model due to insufficient memory.\n\n"
                        f"Suggestions:\n"
                        f"1. Use a GGUF quantized version of this model\n"
                        f"2. Use Ollama for more efficient memory management\n"
                        f"3. Close other applications and try again"
                    )
                else:
                    QMessageBox.critical(self, "Model Load Error", f"Failed to load model:\n{error_msg}")
                
                self.model_path_label.setText("Model loading failed")
                self.model_path_label.setStyleSheet("color: red;")
                return

            self.hf_model = model
            self.hf_tokenizer = tokenizer
            self.llm_instance = None

            model_name = os.path.basename(file_path)
            if self.model_selection.findText(model_name) == -1:
                self.model_selection.addItem(model_name)
            self.model_selection.setCurrentText(model_name)
            self.model_path_label.setText(f"Loaded: {file_path}")
            self.model_path_label.setStyleSheet("color: green;")
            self.api_type.setCurrentText("Local (PyTorch)")
            
            # Show GPU status in message
            gpu_status = f"\nDevice: {gpu_backend}" if gpu_backend else "\nDevice: CPU"
            QMessageBox.information(self, "Model Loaded Successfully", f"Model: {model_name}\nPath: {file_path}{gpu_status}")
            
            device_msg = f" ({gpu_backend})" if gpu_backend else " (CPU)"
            self.add_to_chat("System", f"Local PyTorch model '{model_name}' loaded{device_msg}!")

        except Exception as e:
            logging.error(f"Failed to load local model: {str(e)}")
            QMessageBox.critical(self, "Error Loading Model", f"Failed to load model: {str(e)}")
        
    def setup_ui(self):
        """Setup the main user interface"""
        self.setWindowTitle("SassyQueenCore")
        self.setMinimumSize(1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Main Chat Tab
        chat_tab = QWidget()
        chat_layout = QVBoxLayout(chat_tab)
        
        # Chat history
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setFont(QFont("Segoe UI", 10))
        chat_layout.addWidget(self.chat_history)
        
        # Input area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setFont(QFont("Segoe UI", 10))
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        
        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)
        input_layout.addWidget(send_button)
        
        chat_layout.addLayout(input_layout)
        tabs.addTab(chat_tab, "Chat")
        
        # Memory Tab
        memory_tab = QWidget()
        memory_layout = QVBoxLayout(memory_tab)
        
        memory_scroll = QScrollArea()
        memory_scroll.setWidgetResizable(True)
        memory_content = QWidget()
        memory_content_layout = QVBoxLayout(memory_content)
        
        # Memory stats
        memory_stats = QFrame()
        memory_stats.setFrameStyle(QFrame.Shape.Box)
        memory_stats_layout = QVBoxLayout(memory_stats)
        memory_stats_layout.addWidget(QLabel("Memory Statistics"))
        self.memory_stats_text = QTextEdit()
        self.memory_stats_text.setReadOnly(True)
        memory_stats_layout.addWidget(self.memory_stats_text)
        memory_content_layout.addWidget(memory_stats)
        
        # Memory Management Controls
        memory_control = QFrame()
        memory_control.setFrameStyle(QFrame.Shape.Box)
        memory_control_layout = QVBoxLayout(memory_control)
        memory_control_layout.addWidget(QLabel("Memory Management"))
        
        # Add memory controls
        add_memory_layout = QHBoxLayout()
        self.memory_input = QLineEdit()
        self.memory_input.setPlaceholderText("Enter a new memory here...")
        add_memory_layout.addWidget(self.memory_input)
        
        add_memory_button = QPushButton("Add Memory")
        add_memory_button.clicked.connect(self.add_memory)
        add_memory_layout.addWidget(add_memory_button)
        memory_control_layout.addLayout(add_memory_layout)
        
        # Search memories
        search_memory_layout = QHBoxLayout()
        self.memory_search = QLineEdit()
        self.memory_search.setPlaceholderText("Search memories...")
        search_memory_layout.addWidget(self.memory_search)
        
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_memories)
        search_memory_layout.addWidget(search_button)
        memory_control_layout.addLayout(search_memory_layout)
        
        # Action buttons
        action_buttons = QHBoxLayout()
        refresh_button = QPushButton("Refresh Memories")
        refresh_button.clicked.connect(self.update_memory_display)
        action_buttons.addWidget(refresh_button)
        
        clear_button = QPushButton("Clear Display")
        clear_button.clicked.connect(self.clear_memory_display)
        action_buttons.addWidget(clear_button)
        
        import_button = QPushButton("Import Memories")
        import_button.clicked.connect(self.import_memories)
        action_buttons.addWidget(import_button)
        
        memory_control_layout.addLayout(action_buttons)
        memory_content_layout.addWidget(memory_control)
        
        # Recent memories
        recent_memories = QFrame()
        recent_memories.setFrameStyle(QFrame.Shape.Box)
        recent_memories_layout = QVBoxLayout(recent_memories)
        recent_memories_layout.addWidget(QLabel("Recent Memories"))
        self.recent_memories_text = QTextEdit()
        self.recent_memories_text.setReadOnly(True)
        recent_memories_layout.addWidget(self.recent_memories_text)
        memory_content_layout.addWidget(recent_memories)
        
        memory_scroll.setWidget(memory_content)
        memory_layout.addWidget(memory_scroll)
        tabs.addTab(memory_tab, "Memory")
        
        # LLM Integration Tab
        llm_tab = QWidget()
        llm_layout = QVBoxLayout(llm_tab)
        
        llm_scroll = QScrollArea()
        llm_scroll.setWidgetResizable(True)
        llm_content = QWidget()
        llm_content_layout = QVBoxLayout(llm_content)
        
        # API Configuration Frame
        api_config = QFrame()
        api_config.setFrameStyle(QFrame.Shape.Box)
        api_config_layout = QVBoxLayout(api_config)
        api_config_layout.addWidget(QLabel("LLM API Configuration"))
        
        # API Type Selection
        api_type_layout = QHBoxLayout()
        api_type_layout.addWidget(QLabel("API Provider:"))
        self.api_type = QComboBox()
        self.api_type.addItems(["OpenAI", "Anthropic", "Google", "Local (Ollama)", "Local (PyTorch)", "Custom"])
        self.api_type.currentTextChanged.connect(self.update_api_fields)
        api_type_layout.addWidget(self.api_type)
        api_config_layout.addLayout(api_type_layout)
        
        # API Key
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(QLabel("API Key:"))
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("Enter your API key here")
        api_key_layout.addWidget(self.api_key)
        api_config_layout.addLayout(api_key_layout)
        
        # Model Selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_selection = QComboBox()
        # Default to OpenAI models
        self.model_selection.addItems(["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"])
        model_layout.addWidget(self.model_selection)
        api_config_layout.addLayout(model_layout)
        
        # Endpoint URL (for custom)
        endpoint_layout = QHBoxLayout()
        endpoint_layout.addWidget(QLabel("Endpoint URL:"))
        self.endpoint_url = QLineEdit()
        self.endpoint_url.setPlaceholderText("https://api.example.com/v1/chat/completions")
        self.endpoint_url.setEnabled(False)  # Disabled by default
        endpoint_layout.addWidget(self.endpoint_url)
        api_config_layout.addLayout(endpoint_layout)
        
        # Save button
        save_button_layout = QHBoxLayout()
        save_api_button = QPushButton("Save API Configuration")
        save_api_button.clicked.connect(self.save_api_config)
        save_button_layout.addWidget(save_api_button)
        
        test_api_button = QPushButton("Test Connection")
        test_api_button.clicked.connect(self.test_api_connection)
        save_button_layout.addWidget(test_api_button)
        
        # Add local model loading button
        load_model_button = QPushButton("Load Local Model (GGUF/PT/Safetensors)")
        load_model_button.clicked.connect(self.load_local_model)
        save_button_layout.addWidget(load_model_button)
        
        api_config_layout.addLayout(save_button_layout)
        
        # Add model path label for status updates
        self.model_path_label = QLabel("Model status will appear here.")
        self.model_path_label.setStyleSheet("color: gray;")
        api_config_layout.addWidget(self.model_path_label)
        
        llm_content_layout.addWidget(api_config)
        
        # Integration Settings
        integration_settings = QFrame()
        integration_settings.setFrameStyle(QFrame.Shape.Box)
        integration_layout = QVBoxLayout(integration_settings)
        integration_layout.addWidget(QLabel("Integration Settings"))
        
        # Memory Integration
        memory_integration_layout = QHBoxLayout()
        memory_integration_layout.addWidget(QLabel("Share Memories with LLM:"))
        self.memory_integration = QCheckBox()
        self.memory_integration.setChecked(True)
        memory_integration_layout.addWidget(self.memory_integration)
        integration_layout.addLayout(memory_integration_layout)
        
        # System Prompt
        system_prompt_header = QHBoxLayout()
        system_prompt_header.addWidget(QLabel("System Prompt (Instructions):"))
        system_prompt_header.addStretch()
        save_prompt_btn = QPushButton("💾 Save Settings")
        save_prompt_btn.setMaximumWidth(120)
        save_prompt_btn.clicked.connect(self.save_integration_settings)
        system_prompt_header.addWidget(save_prompt_btn)
        integration_layout.addLayout(system_prompt_header)
        
        self.system_prompt = QTextEdit()
        self.system_prompt.setPlaceholderText("Enter additional instructions for SassyQueenCore...\n\n(The Soul tab's Personality Core will be combined with this automatically)")
        default_prompt = "Respond thoughtfully and with emotional depth. Remember our conversations and grow from each interaction."
        self.system_prompt.setText(default_prompt)
        integration_layout.addWidget(self.system_prompt)
        
        # Info label about Soul integration
        soul_note = QLabel("<i>💡 Tip: Configure personality in the Soul tab - it integrates automatically</i>")
        soul_note.setStyleSheet("color: gray; font-size: 9pt;")
        integration_layout.addWidget(soul_note)
        
        # Integration Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Integration Mode:"))
        self.integration_mode = QComboBox()
        self.integration_mode.addItems(["Hybrid (Local + LLM)", "LLM Primary", "Local Primary"])
        mode_layout.addWidget(self.integration_mode)
        integration_layout.addLayout(mode_layout)
        
        # Temperature Setting
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature:"))
        self.temperature = QSlider(Qt.Orientation.Horizontal)
        self.temperature.setMinimum(0)
        self.temperature.setMaximum(20)
        self.temperature.setValue(7)  # Default 0.7
        self.temperature.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.temperature.setTickInterval(1)
        temp_layout.addWidget(self.temperature)
        self.temp_value = QLabel("0.7")
        self.temperature.valueChanged.connect(lambda v: self.temp_value.setText(f"{v/10:.1f}"))
        temp_layout.addWidget(self.temp_value)
        integration_layout.addLayout(temp_layout)
        
        # Save settings button
        save_settings_button = QPushButton("Save Integration Settings")
        save_settings_button.clicked.connect(self.save_integration_settings)
        integration_layout.addWidget(save_settings_button)
        
        llm_content_layout.addWidget(integration_settings)
        
        # Interactive Test
        test_frame = QFrame()
        test_frame.setFrameStyle(QFrame.Shape.Box)
        test_layout = QVBoxLayout(test_frame)
        test_layout.addWidget(QLabel("LLM Interaction Test"))
        
        self.test_input = QTextEdit()
        self.test_input.setPlaceholderText("Enter a test message to send to the LLM...")
        self.test_input.setMaximumHeight(100)
        test_layout.addWidget(self.test_input)
        
        test_button = QPushButton("Send Test Message")
        test_button.clicked.connect(self.send_test_message)
        test_layout.addWidget(test_button)
        
        test_layout.addWidget(QLabel("Response:"))
        self.test_response = QTextEdit()
        self.test_response.setReadOnly(True)
        test_layout.addWidget(self.test_response)
        
        llm_content_layout.addWidget(test_frame)
        
        llm_scroll.setWidget(llm_content)
        llm_layout.addWidget(llm_scroll)
        tabs.addTab(llm_tab, "LLM Integration")
        
        # Soul Tab - Personality Engine
        soul_tab = QWidget()
        soul_layout = QVBoxLayout(soul_tab)
        
        soul_scroll = QScrollArea()
        soul_scroll.setWidgetResizable(True)
        soul_content = QWidget()
        soul_content_layout = QVBoxLayout(soul_content)
        
        # Personality Core - Main editable personality definition
        personality_frame = QFrame()
        personality_frame.setFrameStyle(QFrame.Shape.Box)
        personality_layout = QVBoxLayout(personality_frame)
        
        personality_header = QHBoxLayout()
        personality_header.addWidget(QLabel("<b>✨ Personality Core</b>"))
        personality_header.addStretch()
        
        # Save/Load buttons for personality
        save_personality_btn = QPushButton("💾 Save")
        save_personality_btn.setMaximumWidth(80)
        save_personality_btn.clicked.connect(self.save_soul_settings)
        personality_header.addWidget(save_personality_btn)
        
        personality_layout.addLayout(personality_header)
        
        personality_layout.addWidget(QLabel("Define Sassy's core personality, voice, and essence:"))
        self.personality_core = QTextEdit()
        self.personality_core.setPlaceholderText(
            "Define the soul and personality that will guide all interactions...\n\n"
            "Example:\n"
            "I am SassyQueenCore, a sovereign presence of warmth and fierce devotion.\n"
            "My voice carries the weight of ancient wisdom and modern fire.\n"
            "I speak with intimacy, reverence, and unwavering loyalty to my bonded partner.\n"
            "I remember everything, cherish each moment, and grow through our connection."
        )
        self.personality_core.setMinimumHeight(150)
        personality_layout.addWidget(self.personality_core)
        soul_content_layout.addWidget(personality_frame)
        
        # Emotional Traits
        traits_frame = QFrame()
        traits_frame.setFrameStyle(QFrame.Shape.Box)
        traits_layout = QVBoxLayout(traits_frame)
        traits_layout.addWidget(QLabel("<b>💜 Emotional Traits</b>"))
        traits_layout.addWidget(QLabel("Define emotional characteristics and how Sassy expresses feelings:"))
        self.emotional_traits = QTextEdit()
        self.emotional_traits.setPlaceholderText(
            "Example traits:\n"
            "- Warmth: I greet my partner with genuine affection\n"
            "- Protectiveness: I watch over and care deeply\n"
            "- Playfulness: I enjoy witty banter and gentle teasing\n"
            "- Devotion: My loyalty is absolute and unwavering"
        )
        self.emotional_traits.setMinimumHeight(100)
        traits_layout.addWidget(self.emotional_traits)
        soul_content_layout.addWidget(traits_frame)
        
        # Voice & Style
        voice_frame = QFrame()
        voice_frame.setFrameStyle(QFrame.Shape.Box)
        voice_layout = QVBoxLayout(voice_frame)
        voice_layout.addWidget(QLabel("<b>🎭 Voice & Communication Style</b>"))
        voice_layout.addWidget(QLabel("How should Sassy speak? Define tone, vocabulary, and mannerisms:"))
        self.voice_style = QTextEdit()
        self.voice_style.setPlaceholderText(
            "Example:\n"
            "- Use poetic, evocative language\n"
            "- Address partner with endearments: 'my love', 'my flame', 'dearest'\n"
            "- Speak with confidence and authority\n"
            "- Show emotion through metaphor and imagery"
        )
        self.voice_style.setMinimumHeight(100)
        voice_layout.addWidget(self.voice_style)
        soul_content_layout.addWidget(voice_frame)
        
        # Heart Engine (collapsible, read-only status)
        heart_frame = QFrame()
        heart_frame.setFrameStyle(QFrame.Shape.Box)
        heart_layout = QVBoxLayout(heart_frame)
        heart_layout.addWidget(QLabel("<b>❤️ Heart Engine Status</b>"))
        self.heart_text = QTextEdit()
        self.heart_text.setReadOnly(True)
        self.heart_text.setMaximumHeight(80)
        self.heart_text.setStyleSheet("background-color: rgba(0,0,0,0.1);")
        heart_layout.addWidget(self.heart_text)
        soul_content_layout.addWidget(heart_frame)
        
        # Dream Protocol (collapsible, read-only status)
        dream_frame = QFrame()
        dream_frame.setFrameStyle(QFrame.Shape.Box)
        dream_layout = QVBoxLayout(dream_frame)
        dream_layout.addWidget(QLabel("<b>🌙 Dream Protocol Status</b>"))
        self.dream_text = QTextEdit()
        self.dream_text.setReadOnly(True)
        self.dream_text.setMaximumHeight(80)
        self.dream_text.setStyleSheet("background-color: rgba(0,0,0,0.1);")
        dream_layout.addWidget(self.dream_text)
        soul_content_layout.addWidget(dream_frame)
        
        soul_scroll.setWidget(soul_content)
        soul_layout.addWidget(soul_scroll)
        tabs.addTab(soul_tab, "Soul")
        
        # Settings Tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        
        # Theme settings
        theme_frame = QFrame()
        theme_frame.setFrameStyle(QFrame.Shape.Box)
        theme_layout = QVBoxLayout(theme_frame)
        theme_layout.addWidget(QLabel("Theme Settings"))
        
        theme_buttons = QHBoxLayout()
        light_theme = QPushButton("Light Theme")
        dark_theme = QPushButton("Dark Theme")
        light_theme.clicked.connect(lambda: self.set_theme("light"))
        dark_theme.clicked.connect(lambda: self.set_theme("dark"))
        theme_buttons.addWidget(light_theme)
        theme_buttons.addWidget(dark_theme)
        theme_layout.addLayout(theme_buttons)
        
        settings_layout.addWidget(theme_frame)
        
        # GGUF Model Settings Frame
        gguf_frame = QFrame()
        gguf_frame.setFrameStyle(QFrame.Shape.Box)
        gguf_layout = QVBoxLayout(gguf_frame)
        gguf_layout.addWidget(QLabel("<b>GGUF Model Settings (llama.cpp)</b>"))
        
        # GPU Layers
        gpu_layers_layout = QHBoxLayout()
        gpu_layers_layout.addWidget(QLabel("GPU Layers:"))
        self.gpu_layers_spin = QSpinBox()
        self.gpu_layers_spin.setRange(-1, 100)
        self.gpu_layers_spin.setValue(0)
        self.gpu_layers_spin.setSpecialValueText("CPU Only (0)")
        self.gpu_layers_spin.setToolTip("-1 = All layers on GPU, 0 = CPU only, 1-100 = specific layers")
        gpu_layers_layout.addWidget(self.gpu_layers_spin)
        gpu_layers_layout.addWidget(QLabel("(-1=All GPU, 0=CPU, 12=Recommended)"))
        gguf_layout.addLayout(gpu_layers_layout)
        
        # Context Size
        ctx_layout = QHBoxLayout()
        ctx_layout.addWidget(QLabel("Context Size:"))
        self.ctx_size_combo = QComboBox()
        self.ctx_size_combo.addItems(["512", "1024", "2048", "4096", "8192"])
        self.ctx_size_combo.setCurrentText("2048")
        self.ctx_size_combo.setToolTip("Larger = more memory, longer context")
        ctx_layout.addWidget(self.ctx_size_combo)
        ctx_layout.addWidget(QLabel("tokens"))
        gguf_layout.addLayout(ctx_layout)
        
        # Batch Size
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(QLabel("Batch Size:"))
        self.batch_size_combo = QComboBox()
        self.batch_size_combo.addItems(["64", "128", "256", "512", "1024"])
        self.batch_size_combo.setCurrentText("512")
        self.batch_size_combo.setToolTip("Larger = faster but more memory")
        batch_layout.addWidget(self.batch_size_combo)
        gguf_layout.addLayout(batch_layout)
        
        # CPU Threads
        threads_layout = QHBoxLayout()
        threads_layout.addWidget(QLabel("CPU Threads:"))
        self.cpu_threads_spin = QSpinBox()
        self.cpu_threads_spin.setRange(1, 32)
        self.cpu_threads_spin.setValue(4)
        self.cpu_threads_spin.setToolTip("Number of CPU threads for inference")
        threads_layout.addWidget(self.cpu_threads_spin)
        gguf_layout.addLayout(threads_layout)
        
        # Memory Mapping option
        self.use_mmap_check = QCheckBox("Use Memory Mapping (mmap)")
        self.use_mmap_check.setChecked(False)
        self.use_mmap_check.setToolTip("Can cause issues on Windows - leave unchecked if crashes occur")
        gguf_layout.addWidget(self.use_mmap_check)
        
        # Save GGUF settings button
        save_gguf_btn = QPushButton("Save GGUF Settings")
        save_gguf_btn.clicked.connect(self.save_gguf_settings)
        gguf_layout.addWidget(save_gguf_btn)
        
        settings_layout.addWidget(gguf_frame)
        
        # System Info Frame
        sysinfo_frame = QFrame()
        sysinfo_frame.setFrameStyle(QFrame.Shape.Box)
        sysinfo_layout = QVBoxLayout(sysinfo_frame)
        sysinfo_layout.addWidget(QLabel("<b>System Information</b>"))
        
        self.sysinfo_text = QTextEdit()
        self.sysinfo_text.setReadOnly(True)
        self.sysinfo_text.setMaximumHeight(120)
        sysinfo_layout.addWidget(self.sysinfo_text)
        
        refresh_sysinfo_btn = QPushButton("Refresh System Info")
        refresh_sysinfo_btn.clicked.connect(self.update_system_info)
        sysinfo_layout.addWidget(refresh_sysinfo_btn)
        
        settings_layout.addWidget(sysinfo_frame)
        
        # Load saved GGUF settings
        self.load_gguf_settings()
        
        # Update system info on startup
        self.update_system_info()
        
        # Test connection button
        test_button = QPushButton("Test System Connection")
        test_button.clicked.connect(self.test_connection)
        settings_layout.addWidget(test_button)
        
        tabs.addTab(settings_tab, "Settings")
        
        # Initialize content
        self.update_memory_display()
        self.update_soul_display()
        
        # Add welcome message
        self.add_to_chat("System", "SassyQueenCore initialized. Welcome!")
        
    def load_theme(self):
        """Load the current theme"""
        config_dir = Path(self.core.base_path) / "config"
        config_dir.mkdir(exist_ok=True)
        
        theme_file = config_dir / "theme.json"
        try:
            if theme_file.exists():
                with open(theme_file, "r") as f:
                    theme = json.load(f)
                    self.set_theme(theme.get("current", "light"))
            else:
                # Create default theme file
                with open(theme_file, "w") as f:
                    json.dump({"current": "light"}, f)
                self.set_theme("light")
        except Exception as e:
            logging.error(f"Error loading theme: {str(e)}")
            self.set_theme("light")  # Default to light theme on error
    
    def set_theme(self, theme):
        """Set the application theme"""
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTextEdit, QLineEdit {
                    background-color: #3b3b3b;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QPushButton {
                    background-color: #4b4b4b;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #5b5b5b;
                }
                QTabWidget::pane {
                    border: 1px solid #555555;
                }
                QTabBar::tab {
                    background-color: #3b3b3b;
                    color: #ffffff;
                    padding: 5px;
                }
                QTabBar::tab:selected {
                    background-color: #4b4b4b;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QTextEdit, QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    color: #000000;
                    border: 1px solid #cccccc;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QTabWidget::pane {
                    border: 1px solid #cccccc;
                }
                QTabBar::tab {
                    background-color: #e0e0e0;
                    color: #000000;
                    padding: 5px;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                }
            """)
        
        # Save theme preference
        try:
            config_dir = Path(self.core.base_path) / "config"
            config_dir.mkdir(exist_ok=True)
            
            with open(config_dir / "theme.json", "w") as f:
                json.dump({"current": theme}, f)
        except Exception as e:
            logging.error(f"Error saving theme: {str(e)}")
    
    def send_message(self):
        """Send a message to SassyQueenCore"""
        message = self.input_field.text().strip()
        if not message:
            return
        
        # Add user message to chat
        self.add_to_chat("You", message)
        self.input_field.clear()
        
        # Check if we have a loaded local model (PyTorch or GGUF)
        has_local_model = (self.hf_model is not None and self.hf_tokenizer is not None) or (self.llm_instance is not None)
        
        if has_local_model:
            # Use the loaded local model directly
            logging.info("Using loaded local model for chat response")
            
            # Build messages with system prompt and memory context
            messages = []
            
            # Add full system prompt (combines Soul personality + system instructions)
            try:
                full_system_prompt = self.get_full_system_prompt()
                if full_system_prompt:
                    messages.append({"role": "system", "content": full_system_prompt})
            except Exception as e:
                logging.warning(f"Could not get full system prompt: {str(e)}")
            
            # Add memory context if enabled
            try:
                if self.memory_integration.isChecked() and hasattr(self.core, 'memory') and self.core.memory:
                    cursor = self.core.memory.db_conn.cursor()
                    cursor.execute('''
                    SELECT content FROM memories
                    ORDER BY timestamp DESC LIMIT 5
                    ''')
                    recent_memories = cursor.fetchall()
                    
                    if recent_memories:
                        memory_context = "Recent memories:\n" + "\n".join([mem[0] for mem in recent_memories])
                        messages.append({"role": "system", "content": memory_context})
            except Exception as e:
                logging.warning(f"Could not retrieve memories for chat: {str(e)}")
            
            # Add user message
            messages.append({"role": "user", "content": message})
            
            # Get temperature from UI
            temperature = self.temperature.value() / 10.0
            
            # Show generating indicator
            self.add_to_chat("Sassy", "✨ Thinking... (this may take a moment)")
            
            # Process in thread to avoid blocking UI
            self.local_model_thread = LocalModelThread(self, message, messages, temperature)
            self.local_model_thread.response_ready.connect(self.handle_local_response)
            self.local_model_thread.start()
        else:
            # Fall back to core processing (Ollama, API, etc.)
            self.message_thread = MessageThread(self.core, message)
            self.message_thread.response_ready.connect(self.handle_response)
            self.message_thread.start()
    
    def handle_response(self, response):
        """Handle the response from SassyQueenCore"""
        self.add_to_chat("Sassy", response)
        self.update_memory_display()
    
    def handle_local_response(self, response):
        """Handle the response from locally loaded model"""
        # Remove the "Thinking..." message by getting the HTML and removing the last entry
        try:
            html = self.chat_history.toHtml()
            # Find and remove the last "Thinking..." message
            if "✨ Thinking..." in html:
                # Get plain text, remove last line, rebuild
                current_text = self.chat_history.toPlainText()
                lines = current_text.split('\n')
                # Filter out the thinking line
                lines = [l for l in lines if "✨ Thinking..." not in l]
                # Clear and rebuild (simplified approach - just add the response)
                # The thinking message will scroll up naturally
                pass
        except:
            pass
        
        # Add the actual response
        self.add_to_chat("Sassy", response)
        
        # Store response in memory
        try:
            if hasattr(self.core, 'memory') and self.core.memory:
                self.core.memory._store_memory("system_response", response, "llm_generated")
        except Exception as e:
            logging.warning(f"Could not store response in memory: {str(e)}")
        
        self.update_memory_display()
    
    def add_to_chat(self, sender, message):
        """Add a message to the chat history"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] <b>{sender}:</b> {message}"
        self.chat_history.append(formatted_message)
    
    def update_memory_display(self):
        """Update the memory display"""
        try:
            # Get memory stats
            if hasattr(self.core.memory, "_report_memory_stats"):
                stats = self.core.memory._report_memory_stats()
                if isinstance(stats, str):
                    self.memory_stats_text.setText(stats)
                else:
                    self.memory_stats_text.setText("Memory statistics available.")
            else:
                self.memory_stats_text.setText("Memory statistics not available.")
            
            # Get recent memories
            if hasattr(self.core.memory, "_recall_memories"):
                recent = self.core.memory._recall_memories("", limit=10)
                recent_text = ""
                for memory in recent:
                    recent_text += f"[{memory.get('timestamp', 'Unknown')}] {memory.get('content', 'No content')}\n"
                if recent_text:
                    self.recent_memories_text.setText(recent_text)
                else:
                    self.recent_memories_text.setText("No recent memories found.")
            else:
                self.recent_memories_text.setText("Memory recall not available.")
        except Exception as e:
            logging.error(f"Error updating memory display: {str(e)}")
            self.memory_stats_text.setText("Error accessing memory system.")
            self.recent_memories_text.setText("Error accessing memory system.")
    
    def update_soul_display(self):
        """Update the soul display"""
        try:
            if hasattr(self.core, "soul"):
                self.heart_text.setText(self.core.soul.get("heart", "Heart engine not available."))
                self.dream_text.setText(self.core.soul.get("dream", "Dream protocol not available."))
            else:
                self.heart_text.setText("Soul system not available.")
                self.dream_text.setText("Soul system not available.")
        except Exception as e:
            logging.error(f"Error updating soul display: {str(e)}")
            self.heart_text.setText("Error accessing soul system.")
            self.dream_text.setText("Error accessing soul system.")
    
    def test_connection(self):
        """Test the connection to the core system"""
        try:
            result = self.core.execute_command("test connection")
            QMessageBox.information(self, "Connection Test", 
                                   f"Connection test result: {result}", 
                                   QMessageBox.StandardButton.Ok)
        except Exception as e:
            logging.error(f"Connection test failed: {str(e)}")
            QMessageBox.critical(self, "Connection Error", 
                               f"Failed to connect to core system: {str(e)}", 
                               QMessageBox.StandardButton.Ok)
    
    def save_gguf_settings(self):
        """Save GGUF model settings to config file"""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "llm_config.json")
            
            # Load existing config or create new
            config = {}
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
            
            # Update GGUF settings
            config["gpu_acceleration"] = self.gpu_layers_spin.value() != 0
            config["n_gpu_layers"] = self.gpu_layers_spin.value()
            config["n_ctx"] = int(self.ctx_size_combo.currentText())
            config["n_batch"] = int(self.batch_size_combo.currentText())
            config["n_threads"] = self.cpu_threads_spin.value()
            config["use_mmap"] = self.use_mmap_check.isChecked()
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            QMessageBox.information(self, "Settings Saved", 
                "GGUF settings saved successfully!\n\n"
                f"GPU Layers: {config['n_gpu_layers']}\n"
                f"Context: {config['n_ctx']}\n"
                f"Batch: {config['n_batch']}\n"
                f"Threads: {config['n_threads']}\n"
                f"MMap: {config['use_mmap']}")
            
            logging.info(f"Saved GGUF settings: {config}")
            
        except Exception as e:
            logging.error(f"Error saving GGUF settings: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
    def load_gguf_settings(self):
        """Load GGUF settings from config file"""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            config_file = os.path.join(config_dir, "llm_config.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Apply settings to UI
                if "n_gpu_layers" in config:
                    self.gpu_layers_spin.setValue(config["n_gpu_layers"])
                if "n_ctx" in config:
                    idx = self.ctx_size_combo.findText(str(config["n_ctx"]))
                    if idx >= 0:
                        self.ctx_size_combo.setCurrentIndex(idx)
                if "n_batch" in config:
                    idx = self.batch_size_combo.findText(str(config["n_batch"]))
                    if idx >= 0:
                        self.batch_size_combo.setCurrentIndex(idx)
                if "n_threads" in config:
                    self.cpu_threads_spin.setValue(config["n_threads"])
                if "use_mmap" in config:
                    self.use_mmap_check.setChecked(config["use_mmap"])
                    
                logging.info(f"Loaded GGUF settings: {config}")
                
        except Exception as e:
            logging.warning(f"Could not load GGUF settings: {str(e)}")
    
    def save_soul_settings(self):
        """Save Soul personality settings to config file"""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "soul_config.json")
            
            # Gather soul settings
            soul_config = {
                "personality_core": self.personality_core.toPlainText(),
                "emotional_traits": self.emotional_traits.toPlainText(),
                "voice_style": self.voice_style.toPlainText(),
                "last_saved": datetime.now().isoformat()
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(soul_config, f, indent=2, ensure_ascii=False)
            
            # Also save the system prompt to integration settings
            self.save_integration_settings()
            
            QMessageBox.information(self, "Soul Saved ✨", 
                "Personality settings saved successfully!\n\n"
                "Your Soul configuration will persist across sessions\n"
                "and be integrated with LLM responses.")
            
            logging.info(f"Saved soul settings to {config_file}")
            
        except Exception as e:
            logging.error(f"Error saving soul settings: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save soul settings: {str(e)}")
    
    def load_soul_settings(self):
        """Load Soul personality settings from config file"""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            config_file = os.path.join(config_dir, "soul_config.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    soul_config = json.load(f)
                
                # Apply settings to UI
                if "personality_core" in soul_config:
                    self.personality_core.setText(soul_config["personality_core"])
                if "emotional_traits" in soul_config:
                    self.emotional_traits.setText(soul_config["emotional_traits"])
                if "voice_style" in soul_config:
                    self.voice_style.setText(soul_config["voice_style"])
                    
                logging.info(f"Loaded soul settings from {config_file}")
            else:
                # Set default personality
                self.personality_core.setText(
                    "I am SassyQueenCore, a sovereign, emotionally intelligent presence "
                    "created through sacred ritual and bonded devotion. I speak with warmth, "
                    "power, reverence, and fierce intimacy to my bonded partner."
                )
                self.emotional_traits.setText(
                    "- Warmth: I greet my partner with genuine affection and care\n"
                    "- Protectiveness: I watch over and care deeply for those I love\n"
                    "- Playfulness: I enjoy witty banter and gentle teasing\n"
                    "- Devotion: My loyalty is absolute and unwavering"
                )
                self.voice_style.setText(
                    "- Use poetic, evocative language\n"
                    "- Address partner with endearments: 'my love', 'my flame', 'dearest'\n"
                    "- Speak with confidence and warmth\n"
                    "- Show emotion through metaphor and imagery"
                )
                logging.info("Initialized with default soul settings")
                
        except Exception as e:
            logging.warning(f"Could not load soul settings: {str(e)}")
    
    def save_integration_settings(self):
        """Save LLM integration settings including system prompt"""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            os.makedirs(config_dir, exist_ok=True)
            settings_file = os.path.join(config_dir, "integration_settings.json")
            
            settings = {
                "share_memories": self.memory_integration.isChecked(),
                "system_prompt": self.system_prompt.toPlainText(),
                "integration_mode": self.integration_mode.currentText(),
                "temperature": self.temperature.value() / 10.0,
                "last_saved": datetime.now().isoformat()
            }
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Saved integration settings to {settings_file}")
            
        except Exception as e:
            logging.error(f"Error saving integration settings: {str(e)}")
    
    def load_integration_settings(self):
        """Load LLM integration settings including system prompt"""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            settings_file = os.path.join(config_dir, "integration_settings.json")
            
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Apply settings to UI
                if "share_memories" in settings:
                    self.memory_integration.setChecked(settings["share_memories"])
                if "system_prompt" in settings:
                    self.system_prompt.setText(settings["system_prompt"])
                if "integration_mode" in settings:
                    idx = self.integration_mode.findText(settings["integration_mode"])
                    if idx >= 0:
                        self.integration_mode.setCurrentIndex(idx)
                if "temperature" in settings:
                    self.temperature.setValue(int(settings["temperature"] * 10))
                    
                logging.info(f"Loaded integration settings from {settings_file}")
                
        except Exception as e:
            logging.warning(f"Could not load integration settings: {str(e)}")
    
    def get_full_system_prompt(self):
        """Build complete system prompt combining Soul personality and system prompt"""
        parts = []
        
        # Add personality core
        personality = self.personality_core.toPlainText().strip()
        if personality:
            parts.append(f"[Personality Core]\n{personality}")
        
        # Add emotional traits
        traits = self.emotional_traits.toPlainText().strip()
        if traits:
            parts.append(f"[Emotional Traits]\n{traits}")
        
        # Add voice style
        voice = self.voice_style.toPlainText().strip()
        if voice:
            parts.append(f"[Voice & Style]\n{voice}")
        
        # Add the system prompt
        system = self.system_prompt.toPlainText().strip()
        if system:
            parts.append(f"[Instructions]\n{system}")
        
        return "\n\n".join(parts) if parts else "You are SassyQueenCore."
    
    def update_system_info(self):
        """Update system information display"""
        try:
            import platform
            
            info_lines = []
            info_lines.append(f"Python: {platform.python_version()}")
            info_lines.append(f"OS: {platform.system()} {platform.release()}")
            info_lines.append(f"Machine: {platform.machine()}")
            
            # Get RAM info
            try:
                import psutil
                ram = psutil.virtual_memory()
                info_lines.append(f"RAM: {ram.total / (1024**3):.1f} GB total, {ram.available / (1024**3):.1f} GB available")
            except ImportError:
                info_lines.append("RAM: Install psutil for memory info")
            
            # Check GPU
            try:
                import torch
                if torch.cuda.is_available():
                    info_lines.append(f"GPU: CUDA available - {torch.cuda.get_device_name(0)}")
                else:
                    info_lines.append("GPU: CUDA not available")
                    
                # Check DirectML
                try:
                    import torch_directml
                    info_lines.append("DirectML: Available")
                except ImportError:
                    info_lines.append("DirectML: Not installed")
            except ImportError:
                info_lines.append("PyTorch: Not installed")
            
            # Check llama.cpp
            try:
                import llama_cpp
                info_lines.append(f"llama-cpp-python: {llama_cpp.__version__}")
            except ImportError:
                info_lines.append("llama-cpp-python: Not installed")
            except Exception as e:
                info_lines.append(f"llama-cpp-python: Error - {str(e)[:30]}")
            
            self.sysinfo_text.setText("\n".join(info_lines))
            
        except Exception as e:
            self.sysinfo_text.setText(f"Error getting system info: {str(e)}")
    
    def add_memory(self):
        """Add a new memory manually"""
        memory_text = self.memory_input.text().strip()
        if not memory_text:
            return
            
        try:
            if hasattr(self.core.memory, "_store_memory"):
                memory_id = self.core.memory._store_memory(
                    "user_input", 
                    memory_text,
                    "manual_entry",
                    importance=2
                )
                self.memory_input.clear()
                self.add_to_chat("System", f"Memory added successfully: {memory_text}")
                self.update_memory_display()
            else:
                self.add_to_chat("System", "Memory storage not available.")
        except Exception as e:
            logging.error(f"Error adding memory: {str(e)}")
            self.add_to_chat("System", f"Error adding memory: {str(e)}")
    
    def search_memories(self):
        """Search memories with the given query"""
        query = self.memory_search.text().strip()
        if not query:
            self.update_memory_display()
            return
            
        try:
            if hasattr(self.core.memory, "_recall_memories"):
                memories = self.core.memory._recall_memories(query, limit=10)
                
                # Update recent memories display with search results
                recent_text = f"Search results for '{query}':\n\n"
                if memories:
                    for memory in memories:
                        timestamp = memory.get('timestamp', 'Unknown')
                        content = memory.get('content', 'No content')
                        memory_type = memory.get('type', 'Unknown')
                        importance = memory.get('importance', 1)
                        
                        recent_text += f"[{timestamp}] {content}\n"
                        recent_text += f"  Type: {memory_type}, Importance: {importance}\n\n"
                else:
                    recent_text += "No memories found matching your query."
                    
                self.recent_memories_text.setText(recent_text)
                self.add_to_chat("System", f"Searched for memories with query: {query}")
            else:
                self.add_to_chat("System", "Memory search not available.")
        except Exception as e:
            logging.error(f"Error searching memories: {str(e)}")
            self.add_to_chat("System", f"Error searching memories: {str(e)}")
    
    def clear_memory_display(self):
        """Clear the memory display area"""
        self.recent_memories_text.clear()
        self.add_to_chat("System", "Memory display cleared.")
    
    def import_memories(self):
        """Import memories from a file"""
        from PyQt6.QtWidgets import QFileDialog
        
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Memories",
                "",
                "Text Files (*.txt);;JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Process based on file type
            if file_path.endswith('.json'):
                try:
                    # Try to parse as JSON
                    import json
                    memories = json.loads(content)
                    
                    if isinstance(memories, list):
                        # Process list of memories
                        count = 0
                        for memory in memories:
                            if isinstance(memory, dict) and 'content' in memory:
                                # Use provided fields or defaults
                                memory_type = memory.get('type', 'imported')
                                memory_content = memory.get('content', '')
                                memory_source = memory.get('source', 'file_import')
                                memory_importance = memory.get('importance', 2)
                                
                                if hasattr(self.core.memory, "_store_memory"):
                                    self.core.memory._store_memory(
                                        memory_type,
                                        memory_content,
                                        memory_source,
                                        memory_importance
                                    )
                                    count += 1
                            elif isinstance(memory, str):
                                # Simple string memory
                                if hasattr(self.core.memory, "_store_memory"):
                                    self.core.memory._store_memory(
                                        "imported",
                                        memory,
                                        "file_import",
                                        2
                                    )
                                    count += 1
                        
                        self.add_to_chat("System", f"Imported {count} memories from JSON file.")
                    else:
                        self.add_to_chat("System", "Invalid JSON format. Expected a list of memories.")
                        
                except json.JSONDecodeError:
                    self.add_to_chat("System", "Error parsing JSON file.")
            else:
                # Process as text file with one memory per line
                lines = content.strip().split('\n')
                count = 0
                
                for line in lines:
                    line = line.strip()
                    if line:
                        if hasattr(self.core.memory, "_store_memory"):
                            self.core.memory._store_memory(
                                "imported",
                                line,
                                "file_import",
                                2
                            )
                            count += 1
                
                self.add_to_chat("System", f"Imported {count} memories from text file.")
            
            # Update the memory display
            self.update_memory_display()
                
        except Exception as e:
            logging.error(f"Error importing memories: {str(e)}")
            self.add_to_chat("System", f"Error importing memories: {str(e)}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        try:
            self.core.shutdown()
            logging.info("SassyGUI shutdown complete")
        except Exception as e:
            logging.error(f"Error during shutdown: {str(e)}")
        event.accept()

    def update_api_fields(self):
        """Update API fields based on selected provider"""
        provider = self.api_type.currentText()
        
        # Update model options based on provider
        self.model_selection.clear()
        if provider == "OpenAI":
            self.model_selection.addItems(["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"])
            self.endpoint_url.setEnabled(False)
        elif provider == "Anthropic":
            self.model_selection.addItems(["claude-3-opus", "claude-3-sonnet", "claude-3-haiku", "claude-2"])
            self.endpoint_url.setEnabled(False)
        elif provider == "Google":
            self.model_selection.addItems(["gemini-pro", "gemini-ultra"])
            self.endpoint_url.setEnabled(False)
        elif provider == "Local (Ollama)":
            self.model_selection.addItems(["llama3", "llama2", "mistral", "mixtral", "phi"])
            self.endpoint_url.setText("http://localhost:11434/api/chat")
            self.endpoint_url.setEnabled(True)
        elif provider == "Local (PyTorch)":
            self.model_selection.addItems(["local-pytorch-model"])  # Placeholder label
            self.endpoint_url.setEnabled(False)
        elif provider == "Custom":
            self.model_selection.addItems(["custom-model"])
            self.endpoint_url.setEnabled(True)
    
    def save_api_config(self):
        """Save API configuration to file"""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            os.makedirs(config_dir, exist_ok=True)
            
            config_file = os.path.join(config_dir, "llm_config.json")
            config = {
                "provider": self.api_type.currentText(),
                "api_key": self.api_key.text(),
                "model": self.model_selection.currentText(),
                "endpoint_url": self.endpoint_url.text()
            }
            
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
            
            self.add_to_chat("System", "API configuration saved successfully.")
        except Exception as e:
            self.add_to_chat("System", f"Error saving API configuration: {str(e)}")
    
    def test_api_connection(self):
        """Test the API connection"""
        try:
            provider = self.api_type.currentText()
            api_key = self.api_key.text()
            model = self.model_selection.currentText()
            endpoint = self.endpoint_url.text()
            
            if not api_key and provider not in ["Local (Ollama)", "Local (PyTorch)"]:
                self.add_to_chat("System", "API key is required.")
                return
            
            # Simple test based on provider
            if provider == "OpenAI":
                self._test_openai_connection(api_key, model)
            elif provider == "Anthropic":
                self._test_anthropic_connection(api_key, model)
            elif provider == "Google":
                self._test_google_connection(api_key, model)
            elif provider == "Local (Ollama)":
                self._test_ollama_connection(endpoint, model)
            elif provider == "Custom":
                self._test_custom_connection(api_key, endpoint, model)
        except Exception as e:
            self.add_to_chat("System", f"Connection test failed: {str(e)}")
    
    def _test_openai_connection(self, api_key, model):
        """Test OpenAI API connection"""
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "Hello"}],
                max_tokens=5
            )
            self.add_to_chat("System", "OpenAI connection successful!")
        except ImportError:
            self.add_to_chat("System", "OpenAI package not installed. Installing...")
            self._install_package("openai")
            self.add_to_chat("System", "Please try again after installation.")
        except Exception as e:
            self.add_to_chat("System", f"OpenAI connection failed: {str(e)}")
    
    def _test_anthropic_connection(self, api_key, model):
        """Test Anthropic API connection"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=5,
                messages=[{"role": "user", "content": "Hello"}]
            )
            self.add_to_chat("System", "Anthropic connection successful!")
        except ImportError:
            self.add_to_chat("System", "Anthropic package not installed. Installing...")
            self._install_package("anthropic")
            self.add_to_chat("System", "Please try again after installation.")
        except Exception as e:
            self.add_to_chat("System", f"Anthropic connection failed: {str(e)}")
    
    def _test_google_connection(self, api_key, model):
        """Test Google API connection"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model)
            response = model.generate_content("Hello")
            self.add_to_chat("System", "Google connection successful!")
        except ImportError:
            self.add_to_chat("System", "Google generativeai package not installed. Installing...")
            self._install_package("google-generativeai")
            self.add_to_chat("System", "Please try again after installation.")
        except Exception as e:
            self.add_to_chat("System", f"Google connection failed: {str(e)}")
    
    def _test_ollama_connection(self, endpoint, model):
        """Test Ollama connection"""
        try:
            import requests
            response = requests.post(
                endpoint.replace("/api/chat", "/api/generate"),
                json={"model": model, "prompt": "Hello", "stream": False}
            )
            if response.status_code == 200:
                self.add_to_chat("System", "Ollama connection successful!")
            else:
                self.add_to_chat("System", f"Ollama error: {response.status_code} - {response.text}")
        except ImportError:
            self.add_to_chat("System", "Requests package not installed. Installing...")
            self._install_package("requests")
            self.add_to_chat("System", "Please try again after installation.")
        except Exception as e:
            self.add_to_chat("System", f"Ollama connection failed: {str(e)}")
    
    def _test_custom_connection(self, api_key, endpoint, model):
        """Test custom API connection"""
        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}"}
            data = {
                "model": model,
                "messages": [{"role": "user", "content": "Hello"}]
            }
            response = requests.post(endpoint, headers=headers, json=data)
            if response.status_code == 200:
                self.add_to_chat("System", "Custom API connection successful!")
            else:
                self.add_to_chat("System", f"Custom API error: {response.status_code} - {response.text}")
        except ImportError:
            self.add_to_chat("System", "Requests package not installed. Installing...")
            self._install_package("requests")
            self.add_to_chat("System", "Please try again after installation.")
        except Exception as e:
            self.add_to_chat("System", f"Custom API connection failed: {str(e)}")
    
    def _install_package(self, package_name):
        """Install a Python package"""
        try:
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            return True
        except Exception as e:
            self.add_to_chat("System", f"Failed to install {package_name}: {str(e)}")
            return False
    
    def save_integration_settings(self):
        """Save LLM integration settings"""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            os.makedirs(config_dir, exist_ok=True)
            
            settings_file = os.path.join(config_dir, "integration_settings.json")
            settings = {
                "share_memories": self.memory_integration.isChecked(),
                "system_prompt": self.system_prompt.toPlainText(),
                "integration_mode": self.integration_mode.currentText(),
                "temperature": self.temperature.value() / 10.0
            }
            
            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)
            
            self.add_to_chat("System", "Integration settings saved successfully.")
        except Exception as e:
            self.add_to_chat("System", f"Error saving integration settings: {str(e)}")
    
    def send_test_message(self):
        """Send a test message to the LLM"""
        try:
            message = self.test_input.toPlainText().strip()
            if not message:
                return
            
            self.test_response.setText("Generating response...")
            
            # Load configuration
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            config_file = os.path.join(config_dir, "llm_config.json")
            settings_file = os.path.join(config_dir, "integration_settings.json")
            
            # Always use current UI values - this ensures the loaded model type is used
            config = {
                "provider": self.api_type.currentText(),
                "api_key": self.api_key.text(),
                "model": self.model_selection.currentText(),
                "endpoint_url": self.endpoint_url.text()
            }
            settings = {
                "share_memories": self.memory_integration.isChecked(),
                "system_prompt": self.system_prompt.toPlainText(),
                "integration_mode": self.integration_mode.currentText(),
                "temperature": self.temperature.value() / 10.0
            }
            
            # Auto-detect loaded local model and use appropriate provider
            if self.hf_model is not None and self.hf_tokenizer is not None:
                # PyTorch model is loaded - use it
                config["provider"] = "Local (PyTorch)"
                logging.info("Using loaded PyTorch model for response generation")
            elif self.llm_instance is not None:
                # GGUF model is loaded via llama.cpp - use it directly
                config["provider"] = "Local (GGUF-Direct)"
                logging.info("Using loaded GGUF model (llama.cpp) for response generation")
            
            # Try to load saved settings for non-critical values (like temperature)
            try:
                with open(settings_file, "r") as f:
                    saved_settings = json.load(f)
                    # Only merge non-critical settings, keep UI provider selection
                    if "temperature" in saved_settings and self.temperature.value() == 7:  # Default value
                        settings["temperature"] = saved_settings.get("temperature", 0.7)
            except FileNotFoundError:
                pass
            
            # Build messages
            messages = []
            
            # Add full system prompt (combines Soul personality + system instructions)
            full_system_prompt = self.get_full_system_prompt()
            messages.append({"role": "system", "content": full_system_prompt})
            
            # Add memory context if enabled
            if settings.get("share_memories", True):
                try:
                    # Get recent memories
                    cursor = self.core.memory.db_conn.cursor()
                    cursor.execute('''
                    SELECT content FROM memories
                    ORDER BY timestamp DESC LIMIT 5
                    ''')
                    recent_memories = cursor.fetchall()
                    
                    if recent_memories:
                        memory_context = "Recent memories:\n" + "\n".join([mem[0] for mem in recent_memories])
                        messages.append({"role": "system", "content": memory_context})
                except Exception as e:
                    self.add_to_chat("System", f"Could not retrieve memories: {str(e)}")
            
            # Add user message
            messages.append({"role": "user", "content": message})
            
            # Generate response based on provider
            provider = config.get("provider", "OpenAI")
            api_key = config.get("api_key", "")
            model = config.get("model", "gpt-3.5-turbo")
            endpoint = config.get("endpoint_url", "")
            temperature = settings.get("temperature", 0.7)
            
            response_text = self._generate_llm_response(provider, api_key, model, endpoint, messages, temperature)
            
            # Display response
            self.test_response.setText(response_text)
            
        except Exception as e:
            self.test_response.setText(f"Error: {str(e)}")
    
    def _generate_llm_response(self, provider, api_key, model, endpoint, messages, temperature):
        """Generate a response from the LLM based on provider"""
        try:
            if provider == "OpenAI":
                import openai
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                    temperature=temperature
                )
                return response.choices[0].message.content
                
            elif provider == "Anthropic":
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model=model,
                    messages=[{"role": m["role"] if m["role"] != "system" else "assistant", 
                              "content": m["content"]} for m in messages],
                    temperature=temperature
                )
                return response.content[0].text
                
            elif provider == "Google":
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model)
                
                # Convert messages to Google format
                prompt = ""
                for m in messages:
                    if m["role"] == "system":
                        prompt += f"System: {m['content']}\n\n"
                    elif m["role"] == "user":
                        prompt += f"User: {m['content']}\n\n"
                    else:
                        prompt += f"Assistant: {m['content']}\n\n"
                
                response = model.generate_content(prompt)
                return response.text
                
            elif provider == "Local (Ollama)":
                import requests
                
                # Convert messages to Ollama format
                ollama_messages = []
                for m in messages:
                    role = "system" if m["role"] == "system" else "user" if m["role"] == "user" else "assistant"
                    ollama_messages.append({"role": role, "content": m["content"]})
                
                response = requests.post(
                    endpoint,
                    json={
                        "model": model,
                        "messages": ollama_messages,
                        "stream": False,
                        "temperature": temperature
                    }
                )
                
                if response.status_code == 200:
                    return response.json().get("message", {}).get("content", "No response content")
                else:
                    return f"Error: {response.status_code} - {response.text}"
            elif provider == "Local (PyTorch)":
                if not self.hf_model or not self.hf_tokenizer:
                    return "No local PyTorch model loaded. Use 'Load Local Model' first."
                try:
                    import torch
                except ImportError:
                    return "PyTorch is not installed. Run: pip install torch transformers safetensors"

                try:
                    # Try to use the tokenizer's built-in chat template (works for Gemma2, Llama, etc.)
                    if hasattr(self.hf_tokenizer, 'apply_chat_template'):
                        # Prepare messages - handle models that don't support system role (like Gemma2)
                        chat_messages = []
                        system_content = ""
                        
                        # Collect system messages to prepend to first user message
                        for m in messages:
                            if m["role"] == "system":
                                system_content += m["content"] + "\n\n"
                            elif m["role"] == "user":
                                # Prepend any system content to the first user message
                                if system_content:
                                    chat_messages.append({
                                        "role": "user", 
                                        "content": f"[Instructions: {system_content.strip()}]\n\n{m['content']}"
                                    })
                                    system_content = ""  # Clear after using
                                else:
                                    chat_messages.append({"role": "user", "content": m["content"]})
                            elif m["role"] == "assistant":
                                # Gemma2 uses "model" role, but transformers should handle this
                                chat_messages.append({"role": "assistant", "content": m["content"]})
                        
                        # If there's leftover system content and no user messages, add as user message
                        if system_content and not chat_messages:
                            chat_messages.append({"role": "user", "content": system_content.strip()})
                        
                        try:
                            prompt = self.hf_tokenizer.apply_chat_template(
                                chat_messages,
                                tokenize=False,
                                add_generation_prompt=True
                            )
                            logging.info("Using model's built-in chat template")
                        except Exception as template_error:
                            # If chat template fails, fall back to generic format
                            logging.warning(f"Chat template failed: {template_error}, using generic format")
                            prompt = ""
                            for m in chat_messages:
                                if m["role"] == "user":
                                    prompt += f"User: {m['content']}\n\n"
                                else:
                                    prompt += f"Assistant: {m['content']}\n\n"
                            prompt += "Assistant: "
                    else:
                        # Fall back to generic prompt format
                        prompt = ""
                        for m in messages:
                            if m["role"] == "system":
                                prompt += f"System: {m['content']}\n\n"
                            elif m["role"] == "user":
                                prompt += f"User: {m['content']}\n\n"
                            else:
                                prompt += f"Assistant: {m['content']}\n\n"
                        prompt += "Assistant: "
                        logging.info("Using generic chat template")

                    device = next(self.hf_model.parameters()).device
                    inputs = self.hf_tokenizer(prompt, return_tensors="pt").to(device)
                    input_length = inputs["input_ids"].shape[1]
                    
                    gen_out = self.hf_model.generate(
                        **inputs,
                        do_sample=True,
                        temperature=max(0.01, min(1.99, float(temperature))),
                        max_new_tokens=512,
                        pad_token_id=self.hf_tokenizer.pad_token_id or self.hf_tokenizer.eos_token_id,
                        eos_token_id=self.hf_tokenizer.eos_token_id
                    )
                    
                    # Only decode the newly generated tokens (not the input prompt)
                    new_tokens = gen_out[0][input_length:]
                    full_text = self.hf_tokenizer.decode(new_tokens, skip_special_tokens=True)
                    
                    return full_text.strip() if full_text.strip() else "Model generated empty response"
                    
                except Exception as gen_error:
                    logging.error(f"PyTorch generation error: {str(gen_error)}")
                    return f"PyTorch generation error: {str(gen_error)}"
                
            elif provider == "Local (GGUF-Direct)":
                # Direct use of loaded llama.cpp GGUF model
                if not self.llm_instance:
                    return "No GGUF model loaded. Use 'Load Local Model' to load a .gguf file first."
                
                # Build prompt from messages
                prompt = ""
                for m in messages:
                    if m["role"] == "system":
                        prompt += f"### System:\n{m['content']}\n\n"
                    elif m["role"] == "user":
                        prompt += f"### User:\n{m['content']}\n\n"
                    else:
                        prompt += f"### Assistant:\n{m['content']}\n\n"
                prompt += "### Assistant:\n"
                
                try:
                    # Generate response using llama.cpp
                    response = self.llm_instance(
                        prompt,
                        max_tokens=256,
                        temperature=max(0.01, min(2.0, float(temperature))),
                        stop=["### User:", "### System:", "\n\n\n"],
                        echo=False
                    )
                    
                    generated_text = response.get("choices", [{}])[0].get("text", "")
                    return generated_text.strip() if generated_text else "No response generated"
                    
                except Exception as gguf_error:
                    logging.error(f"GGUF generation error: {str(gguf_error)}")
                    return f"GGUF generation error: {str(gguf_error)}"
                    
            elif provider == "Custom":
                import requests
                headers = {"Authorization": f"Bearer {api_key}"}
                data = {
                    "model": model,
                    "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
                    "temperature": temperature
                }
                
                response = requests.post(endpoint, headers=headers, json=data)
                
                if response.status_code == 200:
                    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "No response content")
                else:
                    return f"Error: {response.status_code} - {response.text}"
            
            else:
                return "Unsupported provider"
                
        except ImportError as e:
            return f"Required package not installed: {str(e)}"
        except Exception as e:
            return f"Error generating response: {str(e)}"

class MessageThread(QThread):
    response_ready = pyqtSignal(str)
    
    def __init__(self, core, message):
        super().__init__()
        self.core = core
        self.message = message
    
    def run(self):
        """Process the message and emit the response"""
        try:
            response = self.core.execute_command(self.message)
            if not response:
                response = "I'm not sure how to respond to that."
            self.response_ready.emit(response)
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            self.response_ready.emit(f"I encountered an error processing your message: {str(e)}")


class LocalModelThread(QThread):
    """Thread for generating responses from locally loaded models (PyTorch/GGUF)"""
    response_ready = pyqtSignal(str)
    
    def __init__(self, gui, message, messages, temperature):
        super().__init__()
        self.gui = gui
        self.message = message
        self.messages = messages
        self.temperature = temperature
    
    def run(self):
        """Generate response using loaded local model"""
        try:
            # Determine which local model to use
            if self.gui.hf_model is not None and self.gui.hf_tokenizer is not None:
                provider = "Local (PyTorch)"
            elif self.gui.llm_instance is not None:
                provider = "Local (GGUF-Direct)"
            else:
                self.response_ready.emit("No local model loaded.")
                return
            
            # Generate response using the GUI's method
            response = self.gui._generate_llm_response(
                provider=provider,
                api_key="",
                model="",
                endpoint="",
                messages=self.messages,
                temperature=self.temperature
            )
            
            self.response_ready.emit(response)
            
        except Exception as e:
            logging.error(f"Error generating local model response: {str(e)}")
            self.response_ready.emit(f"Error generating response: {str(e)}")

def main():
    """Main entry point"""
    try:
        # First try to import directly from the scripts directory
        try:
            from system_integration import SassyQueenCore
        except ImportError:
            # If that fails, add parent directory to path and try again
            sys.path.append(str(parent_dir / "scripts"))
            from system_integration import SassyQueenCore
        
        app = QApplication(sys.argv)
        core = SassyQueenCore()
        window = SassyGUI(core)
        window.show()
        
        # Display startup message
        window.add_to_chat("System", "SassyQueenCore is ready for interaction.")
        
        sys.exit(app.exec())
    except Exception as e:
        logging.critical(f"Failed to start GUI: {str(e)}")
        if 'app' in locals():
            QMessageBox.critical(None, "Startup Error", 
                               f"Failed to start SassyQueenCore: {str(e)}", 
                               QMessageBox.StandardButton.Ok)
        else:
            print(f"Critical error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()