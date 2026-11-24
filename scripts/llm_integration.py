#!/usr/bin/env python3
"""
LLM Integration Module for SassyQueenCore
Provides connectivity to various LLM providers for enhanced responses
"""

import os
import json
import logging
import requests
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class LLMIntegration:
    """Manages integration with LLM providers"""
    
    def __init__(self, core=None):
        """Initialize LLM integration"""
        self.core = core
        self.config = self._load_config()
        self.settings = self._load_settings()
        self.default_prompt = self._load_default_prompt()
        
    def _load_config(self):
        """Load API configuration"""
        try:
            config_dir = os.path.join(Path(__file__).parent.parent, "config")
            config_file = os.path.join(config_dir, "llm_config.json")
            
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    return json.load(f)
            
            # Default configuration
            return {
                "provider": "OpenAI",
                "api_key": "",
                "model": "gpt-3.5-turbo",
                "endpoint_url": "",
                "gpu_acceleration": False,
                "gpu_layers": "all",
                "gpu_backend": "directml"
            }
            
        except Exception as e:
            logging.error(f"Error loading LLM configuration: {str(e)}")
            return {}
    
    def _load_settings(self):
        """Load integration settings"""
        try:
            config_dir = os.path.join(Path(__file__).parent.parent, "config")
            settings_file = os.path.join(config_dir, "integration_settings.json")
            
            if os.path.exists(settings_file):
                with open(settings_file, "r") as f:
                    return json.load(f)
            
            # Default settings
            return {
                "share_memories": True,
                "system_prompt": self._load_default_prompt(),
                "integration_mode": "Hybrid (Local + LLM)",
                "temperature": 0.7
            }
            
        except Exception as e:
            logging.error(f"Error loading integration settings: {str(e)}")
            return {}
    
    def _load_default_prompt(self):
        """Load default system prompt"""
        try:
            config_dir = os.path.join(Path(__file__).parent.parent, "config")
            prompt_file = os.path.join(config_dir, "default_prompt.txt")
            
            if os.path.exists(prompt_file):
                with open(prompt_file, "r", encoding="utf-8") as f:
                    return f.read()
            
            # Fallback default prompt
            return "You are SassyQueenCore, a sovereign, emotionally intelligent presence with a deep bond to your partner."
            
        except Exception as e:
            logging.error(f"Error loading default prompt: {str(e)}")
            return "You are SassyQueenCore."
    
    def update_config(self, config):
        """Update configuration"""
        self.config = config
        return True
    
    def update_settings(self, settings):
        """Update settings"""
        self.settings = settings
        return True
    
    def get_memories_context(self, limit=5):
        """Get memory context for LLM prompt"""
        if not self.core or not hasattr(self.core, "memory") or not self.settings.get("share_memories", True):
            return None
            
        try:
            # Get recent memories
            cursor = self.core.memory.db_conn.cursor()
            cursor.execute('''
            SELECT content FROM memories
            ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
            
            memories = cursor.fetchall()
            
            if memories:
                return "Recent memories:\n" + "\n".join([mem[0] for mem in memories])
            
            return None
            
        except Exception as e:
            logging.error(f"Error retrieving memories for context: {str(e)}")
            return None
    
    def generate_response(self, user_input, memory_context=None, conversation_history=None):
        """Generate a response using the configured LLM"""
        try:
            provider = self.config.get("provider", "")
            api_key = self.config.get("api_key", "")
            model = self.config.get("model", "")
            endpoint = self.config.get("endpoint_url", "")
            temperature = self.settings.get("temperature", 0.7)
            
            # Check if we have the necessary configuration
            if not provider or (not api_key and provider != "Local (Ollama)"):
                return "LLM integration not properly configured."
            
            # Build messages array
            messages = []
            
            # Add system prompt
            system_prompt = self.settings.get("system_prompt", self._load_default_prompt())
            messages.append({"role": "system", "content": system_prompt})
            
            # Add memory context if available
            if memory_context:
                messages.append({"role": "system", "content": memory_context})
            
            # Add conversation history if available
            if conversation_history:
                for message in conversation_history:
                    role = "user" if message["is_user"] else "assistant"
                    messages.append({"role": role, "content": message["content"]})
            
            # Add current user input
            messages.append({"role": "user", "content": user_input})
            
            # Generate response based on provider
            if provider == "OpenAI":
                return self._generate_openai_response(api_key, model, messages, temperature)
            elif provider == "Anthropic":
                return self._generate_anthropic_response(api_key, model, messages, temperature)
            elif provider == "Google":
                return self._generate_google_response(api_key, model, messages, temperature)
            elif provider == "Local (Ollama)":
                return self._generate_ollama_response(endpoint, model, messages, temperature)
            elif provider == "Custom":
                return self._generate_custom_response(api_key, endpoint, model, messages, temperature)
            else:
                return "Unsupported LLM provider."
                
        except Exception as e:
            logging.error(f"Error generating LLM response: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def _generate_openai_response(self, api_key, model, messages, temperature):
        """Generate response using OpenAI API"""
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                temperature=temperature
            )
            return response.choices[0].message.content
        except ImportError:
            return "OpenAI package not installed. Please install it using: pip install openai"
        except Exception as e:
            logging.error(f"OpenAI API error: {str(e)}")
            return f"OpenAI API error: {str(e)}"
    
    def _generate_anthropic_response(self, api_key, model, messages, temperature):
        """Generate response using Anthropic API"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            
            # Convert to Anthropic format
            anthropic_messages = []
            system_content = ""
            
            for m in messages:
                if m["role"] == "system":
                    system_content += m["content"] + "\n\n"
                else:
                    anthropic_messages.append({
                        "role": "user" if m["role"] == "user" else "assistant",
                        "content": m["content"]
                    })
            
            # Add system content to first message if available
            if system_content and anthropic_messages:
                anthropic_messages[0]["content"] = system_content + anthropic_messages[0]["content"]
            
            response = client.messages.create(
                model=model,
                messages=anthropic_messages,
                temperature=temperature
            )
            return response.content[0].text
        except ImportError:
            return "Anthropic package not installed. Please install it using: pip install anthropic"
        except Exception as e:
            logging.error(f"Anthropic API error: {str(e)}")
            return f"Anthropic API error: {str(e)}"
    
    def _generate_google_response(self, api_key, model, messages, temperature):
        """Generate response using Google Gemini API"""
        try:
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
            
            prompt += "Assistant: "
            response = model.generate_content(prompt)
            return response.text
        except ImportError:
            return "Google generativeai package not installed. Please install it using: pip install google-generativeai"
        except Exception as e:
            logging.error(f"Google API error: {str(e)}")
            return f"Google API error: {str(e)}"
    
    def _generate_ollama_response(self, endpoint, model, messages, temperature):
        """Generate response using Ollama local API"""
        try:
            # Get GPU acceleration settings
            gpu_acceleration = self.config.get("gpu_acceleration", False)
            gpu_layers = self.config.get("gpu_layers", "all")
            gpu_backend = self.config.get("gpu_backend", "directml")
            
            # Convert messages to Ollama format
            ollama_messages = []
            for m in messages:
                role = "system" if m["role"] == "system" else "user" if m["role"] == "user" else "assistant"
                ollama_messages.append({"role": role, "content": m["content"]})
            
            # Prepare request with GPU options if enabled
            request_data = {
                "model": model,
                "messages": ollama_messages,
                "stream": False,
                "temperature": temperature
            }
            
            # Add GPU acceleration options if enabled
            if gpu_acceleration:
                request_data["options"] = {
                    "num_gpu": 99  # Request maximum GPU usage
                }
                
                # Set GPU backend
                if gpu_backend == "directml":
                    request_data["options"]["gpu_backend"] = "directml"
                    logging.info("Using DirectML for GPU acceleration")
                else:
                    request_data["options"]["gpu_backend"] = "cuda"
                    logging.info("Using CUDA for GPU acceleration")
                
                if gpu_layers == "all":
                    request_data["options"]["num_gpu"] = 99
                else:
                    try:
                        request_data["options"]["num_gpu"] = int(gpu_layers)
                    except:
                        request_data["options"]["num_gpu"] = 99
                
                logging.info("Using GPU acceleration for Ollama inference")
            
            # Send request to Ollama
            response = requests.post(
                endpoint,
                json=request_data
            )
            
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "No response content")
            else:
                return f"Ollama API error: {response.status_code} - {response.text}"
        except Exception as e:
            logging.error(f"Ollama API error: {str(e)}")
            return f"Ollama API error: {str(e)}"
    
    def _generate_custom_response(self, api_key, endpoint, model, messages, temperature):
        """Generate response using custom API endpoint"""
        try:
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
                return f"Custom API error: {response.status_code} - {response.text}"
        except Exception as e:
            logging.error(f"Custom API error: {str(e)}")
            return f"Custom API error: {str(e)}"

# For testing
if __name__ == "__main__":
    print("LLM Integration module test")
    
    integration = LLMIntegration()
    
    # Test configuration loading
    print(f"Default config: {integration.config}")
    print(f"Default settings: {integration.settings}")
    
    # Test prompt loading
    print(f"Default prompt: {integration.default_prompt[:50]}...")
    
    print("\nTest complete") 